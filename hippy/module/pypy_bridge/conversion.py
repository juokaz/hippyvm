from hippy.objects.instanceobject import W_InstanceObject as Wph_InstanceObject
from hippy.klass import def_class
from hippy.builtin import wrap, Optional, wrap_method, ThisUnwrapper
from hippy.objects.base import W_Object as WPHP_Object

from pypy.interpreter.baseobjspace import W_Root as Wpy_Root
from pypy.interpreter.module import Module as py_Module

# Note: this module is one of the centre-pieces of a lot of (inevitable)
# circular importing, so we use it as the place to push imports to within
# modules. This not only concentrates the ugliness in one place, but has the
# virtue of doing so in what is one of the simplest files in the whole bridge.


def php_to_py(interp, wph_any):
    from hippy.module.pypy_bridge import php_wrappers, py_wrappers

    phspace = interp.space

    if isinstance(wph_any, php_wrappers.W_PyProxyGeneric):
        return wph_any.wpy_inst
    elif not isinstance(wph_any, WPHP_Object):
        return py_wrappers.W_PHPProxyGeneric(interp, wph_any)

    wph_tp = wph_any.deref().tp
    if wph_tp == phspace.tp_null:
        return interp.pyspace.w_None
    elif wph_tp == phspace.tp_bool:
        return interp.pyspace.wrap(interp.space.is_true(wph_any))
    elif wph_tp == phspace.tp_float:
        return interp.pyspace.newfloat(interp.space.float_w(wph_any))
    elif wph_tp == phspace.tp_int:
        return interp.pyspace.newint(interp.space.int_w(wph_any))
    elif wph_tp == phspace.tp_str:
        return interp.pyspace.wrap(interp.space.str_w(wph_any))
    # XXX disable list conversions
    elif wph_tp == phspace.tp_array:
        # We use the PyPy list strategy system to wrap.
        from hippy.module.pypy_bridge.py_wrappers import make_wrapped_php_array
        return make_wrapped_php_array(interp, wph_any)
    else:
        return py_wrappers.W_PHPProxyGeneric(interp, wph_any)

def py_list_of_ph_array(interp, wph_array):
    wph_elems = wph_array.as_list_w()
    wpy_elems = []
    for i in range(len(wph_elems)):
        wpy_elems.append(php_to_py(interp, wph_elems[i]))
    return interp.pyspace.newlist(wpy_elems)


def py_to_php(interp, wpy_any):
    from hippy.module.pypy_bridge import php_wrappers, py_wrappers
    from pypy.interpreter.function import Function as py_Function

    assert isinstance(wpy_any, Wpy_Root)

    pyspace = interp.pyspace
    if pyspace.is_w(pyspace.type(wpy_any), pyspace.w_bool):
        return interp.space.wrap(interp.pyspace.bool_w(wpy_any))
    elif pyspace.is_w(pyspace.type(wpy_any), pyspace.w_int):
        return interp.space.newint(interp.pyspace.int_w(wpy_any))
    elif pyspace.is_w(pyspace.type(wpy_any), pyspace.w_float):
        return interp.space.newfloat(interp.pyspace.float_w(wpy_any))
    elif pyspace.is_w(pyspace.type(wpy_any), pyspace.w_str):
        return interp.space.wrap(interp.pyspace.str_w(wpy_any))
    elif wpy_any is pyspace.w_None:
        return interp.space.w_Null
    elif pyspace.is_w(pyspace.type(wpy_any), pyspace.w_dict):
        return php_wrappers.W_PyBridgeDictProxy(interp, wpy_any)
    elif pyspace.is_w(pyspace.type(wpy_any), pyspace.w_list):
        return php_wrappers.W_PyBridgeListProxy(interp, wpy_any)
    elif isinstance(wpy_any, py_Function):
        return php_wrappers.W_EmbeddedPyFunc(interp, wpy_any)
    elif isinstance(wpy_any, py_Module):
        return php_wrappers.W_EmbeddedPyMod(interp, wpy_any)
    elif isinstance(wpy_any, py_wrappers.W_PHPProxyGeneric):
        return wpy_any.wph_inst
    else:
        wph_pxy = php_wrappers.W_PyProxyGeneric(php_wrappers.k_PyBridgeProxy, [])
        wph_pxy.setup_instance(interp, wpy_any)
        return wph_pxy

def ph_array_of_py_list(interp, wpy_list):
    wpy_elems = interp.pyspace.listview(wpy_list)
    wph_elems = [ py_to_php(interp, x) for x in wpy_elems ]
    return interp.space.new_array_from_list(wph_elems)

