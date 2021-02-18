from abc import abstractmethod, ABC, ABCMeta
import inspect
from pysv import sv

from ast_tools.stack import SymbolTable
from ast_tools.passes import Pass, PASS_ARGS_T, apply_passes
from ast_tools.common import to_module
import typing as tp

import libcst as cst
import libcst.matchers as match

import magma as m


def _is_leaf_type(T):
    return (issubclass(T, m.Digital) or
            issubclass(T, m.Array) and issubclass(T.T, m.Digital))


def _gen_recursive_args(base_name, T):
    """
    Returns:
        * Flat arguments used for the observe function
        * Nested arguments used to reconstruct the original argument using
          SimpleNamespace for dot notation on products and nested lists for
          arrays
    """
    if _is_leaf_type(T):
        return [base_name], base_name
    if issubclass(T, m.Product):
        flat_args = []
        nested_args = []
        for elem, value in T.field_dict.items():
            _flat_args, _nested_arg = _gen_recursive_args(
                base_name + "_" + elem, value
            )
            flat_args += _flat_args
            nested_args.append(f"{elem}={_nested_arg}")
        return flat_args, f"SimpleNamespace({', '.join(nested_args)})"
    if issubclass(T, m.Tuple):
        flat_args = []
        nested_args = []
        for i, value in enumerate(T.fields):
            _flat_args, _nested_arg = _gen_recursive_args(
                base_name + "_" + str(i), value
            )
            flat_args += _flat_args
            nested_args.append(_nested_arg)
        return flat_args, f"({', '.join(nested_args)},)"
    if issubclass(T, m.Array):
        flat_args = []
        nested_args = []
        for i in range(len(T)):
            _flat_args, _nested_arg = _gen_recursive_args(
                base_name + "_" + str(i), T.T
            )
            flat_args += _flat_args
            nested_args.append(_nested_arg)
        return flat_args, f"[{', '.join(nested_args)}]"

    raise TypeError(T)


class PysvMonitor(ABC, metaclass=ABCMeta):
    @abstractmethod
    def observe(self, *args, **kwargs):
        pass


class MonitorTransformer(cst.CSTTransformer):
    def __init__(self, env, metadata):
        self.env = env
        self.metadata = metadata

    def leave_FunctionDef(self, original_node, updated_node):
        """
        Transforms the observe function to accept the flattened version of
        arguments (e.g. product leaf ports).  Inserts code into the beginning
        of the function to reconstruct the original argument using
        SimpleNamespace to provide dot notation
        """
        if match.matches(updated_node.name,
                         match.Name("observe")):
            params = updated_node.params.params
            assert match.matches(params[0], match.Param(match.Name("self")))
            # Keep around the original arguments since this will be needed by
            # the monitor peek logic (requires the unflattened arguments
            self.metadata["_orig_observe_args_"] = [param.name.value
                                                    for param in params]
            new_params = [params[0]]
            prelude = [
                cst.parse_statement("from types import SimpleNamespace")
            ]
            for param in params[1:]:
                if param.annotation is None:
                    new_params.append(param)
                else:
                    T = eval(to_module(param.annotation.annotation).code,
                             dict(self.env))
                    if _is_leaf_type(T):
                        new_params.append(param)
                        continue
                    flat_args, nested_args = _gen_recursive_args(
                        param.name.value, T)
                    new_params.extend(
                        cst.Param(cst.Name(arg)) for arg in flat_args)
                    prelude.append(
                        cst.parse_statement(
                            f"{param.name.value} = {nested_args}"))
            return updated_node.with_changes(
                params=updated_node.params.with_changes(params=new_params),
                body=updated_node.body.with_changes(
                    body=tuple(prelude) + updated_node.body.body)
            )
        return updated_node


class MonitorPass(Pass):
    def rewrite(self,
                tree: cst.CSTNode,
                env: SymbolTable,
                metadata: tp.MutableMapping) -> PASS_ARGS_T:
        tree = tree.visit(MonitorTransformer(env, metadata))
        return tree, env, metadata


class python_monitor(apply_passes):
    def __init__(self, pre_passes=[], post_passes=[],
                 debug: bool = False,
                 env: tp.Optional[SymbolTable] = None,
                 path: tp.Optional[str] = None,
                 file_name: tp.Optional[str] = None
                 ):
        passes = pre_passes + [MonitorPass()] + post_passes
        super().__init__(passes=passes, env=env, debug=debug, path=path,
                         file_name=file_name)

    def exec(self,
             etree: tp.Union[cst.ClassDef, cst.FunctionDef],
             stree: tp.Union[cst.ClassDef, cst.FunctionDef],
             env: SymbolTable,
             metadata: tp.MutableMapping):
        result = super().exec(etree, stree, env, metadata)
        result.observe._orig_args_ = metadata["_orig_observe_args_"]
        result._source_code_ = to_module(stree).code
        return result
