"""툴 자동 등록"""
import importlib
import inspect
import pkgutil
from types import ModuleType

from src.agent import tools

REQUIRED_ATTRIBUTES = ('FUNCTION_NAME', 'DECLARATION', 'ARGUMENTS', 'run')


def load_tool_modules() -> list[ModuleType]:
    """_로 시작하는 파일은 템플릿·내부 모듈이라 건너뛴다."""
    modules = []
    for module_info in pkgutil.iter_modules(tools.__path__):
        if module_info.name.startswith('_'):
            continue
        modules.append(importlib.import_module(f'{tools.__name__}.{module_info.name}'))
    return modules


def check_contract(module: ModuleType) -> None:
    """툴 파일 하나의 계약을 검사한다. 어긋나면 예외."""
    where = module.__name__

    missing = [name for name in REQUIRED_ATTRIBUTES if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f'{where}: {missing} 가 없다. _template.py의 이름을 그대로 써야 한다')

    function_name = module.FUNCTION_NAME
    declared_name = module.DECLARATION.get('name')
    if function_name != declared_name:
        raise RuntimeError(
            f'{where}: FUNCTION_NAME({function_name})과 '
            f'DECLARATION["name"]({declared_name})이 다르다. '
            'LLM이 부르는 이름과 등록되는 이름이 갈린다'
        )

    argument_fields = set(module.ARGUMENTS.model_fields)
    run_parameters = set(inspect.signature(module.run).parameters)
    if argument_fields != run_parameters:
        raise RuntimeError(
            f'{where}: ARGUMENTS 필드와 run() 파라미터가 다르다 '
            f'(차집합 {argument_fields ^ run_parameters}). '
            '검증은 통과하고 실행에서 TypeError가 난다'
        )

    declared_properties = set(module.DECLARATION['parameters']['properties'])
    unknown = declared_properties - argument_fields
    if unknown:
        raise RuntimeError(
            f'{where}: DECLARATION에만 있고 ARGUMENTS에 없는 인자 {sorted(unknown)}. '
            "LLM이 그 인자를 넣으면 extra='forbid'에 걸려 전부 거절된다"
        )


def build_registry() -> tuple[list[dict], dict, dict]:
    """등록 대상을 모으고 계약을 검사한다."""
    declarations, function_map, argument_models = [], {}, {}

    for module in load_tool_modules():
        check_contract(module)

        function_name = module.FUNCTION_NAME
        if function_name in function_map:
            raise RuntimeError(
                f'{module.__name__}: 함수 이름 {function_name}이 중복됐다. '
                '나중에 등록된 툴이 앞의 것을 덮어쓴다'
            )

        declarations.append(module.DECLARATION)
        function_map[function_name] = module.run
        argument_models[function_name] = module.ARGUMENTS

    return declarations, function_map, argument_models


TOOLS, FUNCTION_MAP, ARGUMENT_MODELS = build_registry()


if __name__ == '__main__':
    from config import print_title

    print_title(f'등록된 툴 {len(TOOLS)}개')
    for declaration in TOOLS:
        name = declaration['name']
        properties = declaration['parameters']['properties']
        required = declaration['parameters'].get('required', [])
        print(f'  {name}')
        print(f'    인자   {len(properties)}개 (필수 {len(required)}: {required})')
        print(f'    설명   {declaration["description"][:70]}')
        print()
