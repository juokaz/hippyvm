from testing.test_interpreter import BaseTestInterpreter
import pytest

class TestPyPyBridge(BaseTestInterpreter):

    @pytest.fixture
    def php_space(self):
        return self.space

    def test_import_py_mod_func(self, php_space):
        output = self.run('''
            $math = import_py_mod("math");
            echo($math->pow(2, 3));
        ''')
        assert php_space.int_w(output[0]) == 8

    def test_import_py_mod_fails(self, php_space):
        output = self.run('''
            try {
                $m = import_py_mod("__ThIs_DoEs_NoT_ExIsT");
                echo "FAIL";
            } catch(PyException $e) {
                echo $e->getMessage();
            }
        ''')
        err_s = "No module named __ThIs_DoEs_NoT_ExIsT"
        assert php_space.str_w(output[0]) == err_s

    def test_import_py_mod_attr(self, php_space):
        import math
        output = self.run('''
            $math = import_py_mod("math");
            echo($math->pi);
        ''')
        assert php_space.float_w(output[0]) == math.pi

    def test_import_py_nested1_mod_func(self, php_space):
        output = self.run('''
            $os_path = import_py_mod("os.path");
            echo($os_path->join("a", "b"));
        ''')
        assert php_space.str_w(output[0]) == "a/b"

    def test_import_py_nested2_mod_func(self, php_space):
        output = self.run('''
            $os = import_py_mod("os");
            echo($os->path->join("a", "b"));
        ''')
        assert php_space.str_w(output[0]) == "a/b"

    def test_embed_py_mod(self, php_space):
        output = self.run('''
            $m = embed_py_mod("mymod", "def f(): print('hello')");
            echo($m->f());
        ''')
        assert output[0] == self.space.w_Null # XXX for now

    def test_call_func_int_args(self, php_space):
        output = self.run('''
            $m = embed_py_mod("mymod", "def f(x): return x+1");
            echo($m->f(665));
        ''')
        assert php_space.int_w(output[0]) == 666

    def test_multiple_modules(self, php_space):
        output = self.run('''
            $m1 = embed_py_mod("mod1", "def f(x): return x+1");
            $m2 = embed_py_mod("mod2", "def g(x): return x-1");
            echo($m1->f(665));
            echo($m2->g(665));
        ''')
        assert php_space.int_w(output[0]) == 666
        assert php_space.int_w(output[1]) == 664

    def test_modules_intercall(self, php_space):
        output = self.run('''
            $m1 = embed_py_mod("mod1", "def f(x): return x+1");
            $m2 = embed_py_mod("mod2",
                "import mod1\ndef g(x): return mod1.f(x)");
            echo($m2->g(1336));
        ''')
        assert php_space.int_w(output[0]) == 1337

    def test_modules_intercall2(self, php_space):
        output = self.run('''
            $m1 = embed_py_mod("mod1", "def f(x): return x+1");
            $m2 = embed_py_mod("mod2",
                "import mod1\ndef g(x): return mod1.f(x)");
            $m3 = embed_py_mod("mod3",
                "import mod2\ndef h(x): return mod2.g(x)");
            echo($m3->h(41));
        ''')
        assert php_space.int_w(output[0]) == 42

    def test_fib(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def fib(n):
                if n == 0: return 0
                if n == 1: return 1
                return fib(n-1) + fib(n-2)
            EOD;

            $m = embed_py_mod("fib", $src);
            $expects = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144];

            for ($i = 0; $i < count($expects); $i++) {
                assert($m->fib($i) == $expects[$i]);
            }
        ''')

    def test_multitype_args(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def cat(s, b, i):
                return "%s-%s-%s" % (s, b, i)
            EOD;

            $m = embed_py_mod("meow", $src);
            echo($m->cat("123", True, 666));
        ''')
        assert php_space.str_w(output[0]) == "123-True-666"

    def test_variadic_args(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def cat(*args):
                return "-".join([str(x) for x in args])
            EOD;

            $m = embed_py_mod("meow", $src);
            echo($m->cat(5, 4, 3, 2, 1, "Thunderbirds", "Are", "Go"));
        ''')
        assert php_space.str_w(output[0]) == "5-4-3-2-1-Thunderbirds-Are-Go"

    def test_kwargs_exhaustive(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def cat(x="111", y="222", z="333"):
                return "-".join([x, y, z])
            EOD;

            $m = embed_py_mod("meow", $src);
            echo($m->cat("abc", "def", "ghi"));
        ''')
        assert php_space.str_w(output[0]) == "abc-def-ghi"

    def test_kwargs_nonexhaustive(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def cat(x="111", y="222", z="333"):
                return "-".join([x, y, z])
            EOD;

            $m = embed_py_mod("meow", $src);
            echo($m->cat("abc", "def"));
        ''')
        assert php_space.str_w(output[0]) == "abc-def-333"

    def test_kwargs_on_py_proxy(self, php_space):
        output = self.run('''
            $mod = import_py_mod("itertools");
            $src = <<<EOD
            def f(mod):
                it = mod.count(step=666) # should not explode
                vs = [ it.next() for i in range(3) ]
                return vs[-1]
            EOD;
            $f = embed_py_func($src);
            echo($f($mod));
        ''')
        assert php_space.int_w(output[0]) == 1332

    def test_kwargs_on_py_proxy2(self, php_space):
        output = self.run('''
            $mod = import_py_mod("itertools");
            $src = <<<EOD
            def f():
                it = mod.count(step=666) # should not explode
                vs = [ it.next() for i in range(3) ]
                return vs[-1]
            EOD;
            $f = embed_py_func($src);
            echo($f());
        ''')
        assert php_space.int_w(output[0]) == 1332

    def test_kwargs_on_py_proxy3(self, php_space):
        output = self.run('''
            $f = embed_py_func("def f(a, b=0, c=0): return a + b + c");
            $g = embed_py_func("def g(): return f(1, c=3)");
            echo($g());
        ''')
        assert php_space.int_w(output[0]) == 4

    def test_kwargs_on_py_proxy4(self, php_space):
        output = self.run('''
            $mk_src = <<<EOD
            def mk():
                code = 'def f(a, b=0, c=0): return a + b + c'
                import imp
                flibble = imp.new_module('flibble')
                exec code in flibble.__dict__
                return flibble
            EOD;
            $mk = embed_py_func($mk_src);
            $mod = $mk();

            $g = embed_py_func("def g(): return mod.f(1, c=3)");
            echo($g());
        ''')
        assert php_space.int_w(output[0]) == 4

    def test_phbridgeproxy_equality1(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def cmp(x, y):
                return x == y
            EOD;
            $cmp = embed_py_func($src);

            class C { }
            $x = new C();
            echo($cmp($x, $x));
        ''')
        assert php_space.is_true(output[0])

    def test_phbridgeproxy_equality2(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def cmp(x, y):
                return x == y
            EOD;
            $cmp = embed_py_func($src);

            class C { }
            $x = new C();
            $y = new C();
            echo($cmp($x, $y));
        ''')
        assert php_space.is_true(output[0])

    def test_phbridgeproxy_nequality1(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def cmp(x, y):
                return x == y
            EOD;
            $cmp = embed_py_func($src);

            class C {
                public $val;
                function __construct($val) {
                    $this->val = $val;
                }
            }
            $x = new C(1);
            $y = new C(2);
            echo($cmp($x, $y));
        ''')
        assert not php_space.is_true(output[0])

    def test_phbridgeproxy_nequality2(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def cmp(x, y):
                return x == y
            EOD;
            $cmp = embed_py_func($src);

            class C {
                public $val;
                function __construct($val) {
                    $this->val = $val;
                }
            }
            $x = new C(1);
            $y = new C(1);
            echo($cmp($x, $y));
        ''')
        assert php_space.is_true(output[0])

    def test_phbridgeproxy_instanceof(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def iof(a):
                return isinstance(a, C)
            EOD;

            $iof = embed_py_func($src);

            class C {}
            class D {}
            $x = new C;
            $y = new D;
            echo($iof($x));
            echo($iof($y));
        ''')
        assert php_space.is_true(output[0])
        assert not php_space.is_true(output[1])

    def test_phbridgeproxy_id1(self, php_space):
        output = self.run('''
            $src = <<<EOD
            @php_refs('x', 'y')
            def is_chk(x, y):
                return str(id(x) == id(y))
            EOD;
            $is_chk = embed_py_func($src);

            class C {}
            $x = new C;
            $y = new c;
            echo($is_chk($x, $y) . " " . $is_chk($x, $x));
        ''')
        assert php_space.str_w(output[0]) == "False True"

    def test_phbridgeproxy_id2(self, php_space):
        output = self.run('''
            function f() {}
            function g() {}

            $src = <<<EOD
            def is_chk():
                return "%s %s" % (str(id(f) == id(g)), str(id(f) == id(f)))
            EOD;
            $is_chk = embed_py_func($src);

            echo($is_chk());
        ''')
        assert php_space.str_w(output[0]) == "False True"

    def test_phbridgeproxy_id3(self, php_space):
        output = self.run('''
            $src = <<<EOD
            @php_refs('x', 'y')
            def is_chk(x, y):
                return str(id(x) == id(y))
            EOD;
            $is_chk = embed_py_func($src);

            class C {}
            $x = new C;
            $y = new c;
            echo($is_chk($x, $y) . " " . $is_chk($x, $x));
        ''')
        assert php_space.str_w(output[0]) == "False True"


    def test_phbridgeproxy_is1(self, php_space):
        output = self.run('''
            $src = <<<EOD
            @php_refs('x', 'y')
            def is_chk(x, y):
                return str(x is y)
            EOD;
            $is_chk = embed_py_func($src);

            class C {}
            $x = new C;
            $y = new c;
            echo($is_chk($x, $y) . " " . $is_chk($x, $x));
        ''')
        assert php_space.str_w(output[0]) == "False True"

    def test_phbridgeproxy_is2(self, php_space):
        output = self.run('''
            function f() {}
            function g() {}

            $src = <<<EOD
            def is_chk():
                return "%s %s" % (str(f is g), str(f is f))
            EOD;
            $is_chk = embed_py_func($src);

            echo($is_chk());
        ''')
        assert php_space.str_w(output[0]) == "False True"

    def test_phbridgeproxy_is3(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def is_chk(x, y):
                return str(x is y)
            EOD;
            $is_chk = embed_py_func($src);

            class C {}
            $x = new C;
            $y = new c;
            echo($is_chk($x, $y) . " " . $is_chk($x, $x));
        ''')
        assert php_space.str_w(output[0]) == "False True"

    def test_callback_to_php(self, php_space):
        output = self.run('''
            function hello() {
                echo "foobar";
            }

            $src = <<<EOD
            def call_php():
                hello()
            EOD;

            $call_php = embed_py_func($src);
            $call_php();
        ''')
        assert php_space.str_w(output[0]) == "foobar"

    # XXX Test kwargs

    def test_obj_proxy(self, php_space):
        output = self.run('''
            $src = <<<EOD
            import sys
            def get():
                return sys
            EOD;
            $m = embed_py_mod("m", $src);
            echo($m->get()->__name__);
        ''')
        assert php_space.str_w(output[0]) == "sys"

    def test_embed_py_func(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def test():
                return "jibble"
            EOD;
            $test = embed_py_func($src);
            echo($test());
        ''')
        assert php_space.str_w(output[0]) == "jibble"

    def test_embed_py_func_accepts_only_a_func(self, php_space):
        output = self.run('''
            $src = <<<EOD
            import os # <--- nope
            def test():
                return "jibble"
            EOD;

            try {
                $test = embed_py_func($src);
                echo "test failed";
            } catch(BridgeException $e) {
                echo $e->getMessage();
            }
        ''')
        err_s = "embed_py_func: Python source must define exactly one function"
        assert php_space.str_w(output[0]) == err_s

    def test_embed_py_func_accepts_only_a_func2(self, php_space):
        output = self.run('''
            $src = "import os"; // not a func
            try {
                $test = embed_py_func($src);
            } catch(BridgeException $e) {
                echo $e->getMessage();
            }
        ''')
        err_s = "embed_py_func: Python source must define exactly one function"
        assert php_space.str_w(output[0]) == err_s

    def test_embed_py_func_args(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def cat(x, y, z):
                return "%s-%s-%s" % (x, y, z)
            EOD;
            $cat = embed_py_func($src);
            echo($cat("t", "minus", 10));
        ''')
        assert php_space.str_w(output[0]) == "t-minus-10"

    def test_return_function_to_php(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def cwd():
                import os
                return os.getpid
            EOD;

            $cwd = embed_py_func($src);
            $x = $cwd();
            echo $x();
        ''')
        import os
        assert php_space.int_w(output[0]) == os.getpid()

    def test_embed_php_func(self, php_space):
        output = self.run('''
            $pysrc = <<<EOD
            def f():
                php_src = "function g(\$a, \$b) { return \$a + \$b; }"
                g = embed_php_func(php_src)
                return g(5, 4)
            EOD;

            $f = embed_py_func($pysrc);
            echo $f();
        ''')
        assert php_space.int_w(output[0]) == 9

    def test_embed_py_func(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def f(a, b):
                return sum([a, b])
            EOD;

            $f = embed_py_func($src);
            echo $f(4, 7);
        ''')
        assert php_space.int_w(output[0]) == 11

    def test_embed_py_func_global(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def test():
                return "jibble"
            EOD;
            embed_py_func_global($src);
            echo(test());
        ''')
        assert php_space.str_w(output[0]) == "jibble"

    def test_embed_py_func_global_returns_nothing(self, php_space):
        output = self.run('''
            $src = <<<EOD
            def test(): pass
            EOD;
            $r = embed_py_func_global($src);
            echo($r);
        ''')
        assert php_space.w_Null == output[0]

    def test_embed_py_meth(self, php_space):
        output = self.run('''
            class C {};

            $src = <<<EOD
            def myMeth(self):
                return 10
            EOD;
            embed_py_meth("C", $src);
            $c = new C();
            echo($c->myMeth());
        ''')
        assert php_space.int_w(output[0]) == 10

    def test_embed_py_meth_subclass(self, php_space):
        output = self.run('''
            {
            class C {};

            $src = <<<EOD
            def myMeth(self):
                return 10
            EOD;
            embed_py_meth("C", $src);

            class D extends C {};

            $d = new D();
            echo($d->myMeth());
            }
        ''')
        assert php_space.int_w(output[0]) == 10

    def test_embed_py_meth_attr_access(self, php_space):
        output = self.run('''
            class A {
                function __construct() {
                    $this->v = 666;
                }
            };
            $a = new A();

            class B {
            };

            $src = <<<EOD
            def bMeth(self):
                # We should pick up global dollar a, not class A.
                # Hippy class/func names are canonicalised lower case.
                a.v = 777
                return a.v
            EOD;
            embed_py_meth("B", $src);

            $b = new B();
            echo $b->bMeth();
        ''')
        assert php_space.int_w(output[0]) == 777

    def test_embed_py_meth_attr_overide(self, php_space):
        output = self.run('''
            class A {
                function m() { return 666; }
            };
            $a = new A();

            class B extends A {};

            $src = "def m(self): return 667";
            embed_py_meth("B", $src);

            $b = new B();
            echo $b->m();
        ''')
        assert php_space.int_w(output[0]) == 667

    def test_embed_py_meth_ctor(self, php_space):
        output = self.run('''
            class A {
            };
            $a = new A();

            $src = "def __construct(self): self.x = 666";
            embed_py_meth("A", $src);

            $a = new A();
            echo $a->x;
        ''')
        assert php_space.int_w(output[0]) == 666

    def test_embed_py_meth_attr_access_other_inst(self, php_space):
        output = self.run('''
        {
            class A {
                    public $x = 666;
            };

            class B { }

            $src = "def f(self, other): return other.x";
            embed_py_meth("B", $src);

            $a = new A();
            $b = new B();
            echo $b->f($a);
        }
        ''')
        assert php_space.int_w(output[0]) == 666
