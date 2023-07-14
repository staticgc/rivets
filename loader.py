import sys
import os

from unit import Step, FunctionUnit, FlowUnit
from context import Context
import importlib

def resolve_fn(f: str):
    parts = f.rsplit(sep='.', maxsplit=1)
    if len(parts) == 1:
        print(locals())
        return locals()[parts[0]]
    elif len(parts) == 2:
        mod = importlib.import_module(parts[0])
        fname = parts[1]
        return getattr(mod, fname)
    else:
        raise Exception("failed to parse function name {0}".format(f))



def parse_step(d: dict, desc: str) -> Step:
    name = d.get('$name', desc)
    try:
        del d['$name']
    except KeyError:
        pass

    return Step(name, desc, d)

def parse_unit(d: dict, name: str):
    desc = d.get('desc', "")
    inp = d.get('in', {})
    out = d.get('out', {})
    args = d.get('args', [])
    defaults = d.get('defs', {})

    fname = d.get('fn', None)
    if fname:
        is_meta = d.get('meta', False)
        map_op = d.get('map_op', False)
        fn = resolve_fn(fname)
        u = FunctionUnit(fn, is_meta, map_op, name, desc, inp, out, args, defaults)
        return u
    
    step_list = d.get('steps', None)
    if step_list:
        steps = []
        for s in step_list:
            for step_desc, step_def in s.items():
                steps.append(parse_step(step_def, step_desc))

        u = FlowUnit(steps, name, desc, inp, out, args, defaults)
        return u 

    raise Exception("unknown unit type name={0}".format(name))    

def parse_units(d: dict[str]):
    umap = {}
    for name, udef in d.items():
        u = parse_unit(udef, name)
        umap[name] = u
    return umap


def find_cfg_file(cfg_file: str):
    for p in sys.path:
        path = os.path.join(p, cfg_file)
        if os.path.exists(path):
            return path
    return None



def load_config(ctx: Context, cfg_file_path: str, config_file_loader, processed_cfg = None):
    if processed_cfg is None:
        processed_cfg = {}

    base_cfg_file = os.path.basename(cfg_file_path)

    ctx.log.info("loading config name=%s path=%s, processed=%s", base_cfg_file, os.path.dirname(cfg_file_path), processed_cfg)

    if base_cfg_file in processed_cfg:
        if processed_cfg[base_cfg_file] == 'in-process':
            raise Exception("cyclic import detected {0}".format(base_cfg_file))
        
        if processed_cfg[base_cfg_file] == 'done':
            return

    d = config_file_loader(cfg_file_path)


    if 'imports' in d:
        for parent_cfg in d['imports']:
            full_path = find_cfg_file(parent_cfg)

            if full_path:
                load_config(ctx, full_path, config_file_loader, processed_cfg)
        
        del d['imports']

    umap = parse_units(d)
    ctx.add_umap(umap)
    processed_cfg[base_cfg_file] = 'done'

def load_std_config(ctx: Context, loader):
    cfg_file = find_cfg_file('std.yml')
    load_config(ctx, cfg_file, loader, {})