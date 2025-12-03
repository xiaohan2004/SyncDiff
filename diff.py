import os
import re
import hashlib
import configparser
from datetime import datetime

def get_md5(path, chunk=4096):
    """计算文件 MD5"""
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        while data := f.read(chunk):
            md5.update(data)
    return md5.hexdigest()

def get_file_info(file_path):
    """获取文件详细信息：大小 + 修改时间"""
    try:
        stat = os.stat(file_path)
        size = stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return size, mtime
    except Exception as e:
        return None, None

def parse_ignore_rules(rule_string):
    """原生正则表达式解析，不做任何转换"""
    rules = rule_string.split(";") if rule_string else []
    return [re.compile(r.strip()) for r in rules if r.strip()]

def should_ignore(path, rules):
    """判断路径是否被忽略"""
    return any(r.search(path) for r in rules)

def collect_files(base, rules):
    files = {}
    for root, dirs, fs in os.walk(base):
        rel_dir = os.path.relpath(root, base)

        if rel_dir != "." and should_ignore(rel_dir, rules):
            continue

        for f in fs:
            rel = os.path.relpath(os.path.join(root, f), base)
            if not should_ignore(rel, rules):
                files[rel] = os.path.join(root, f)
    return files

def compare(folder_a, folder_b, name_a, name_b, rules, job_name):
    print(f"\n==== 🆚 开始对比：{job_name} ({name_a} vs {name_b}) ====")
    files_a = collect_files(folder_a, rules)
    files_b = collect_files(folder_b, rules)

    all_paths = sorted(set(files_a) | set(files_b))

    for rel in all_paths:
        pa, pb = files_a.get(rel), files_b.get(rel)

        if pa and pb:
            md5_a, md5_b = get_md5(pa), get_md5(pb)
            if md5_a != md5_b:
                size_a, mtime_a = get_file_info(pa)
                size_b, mtime_b = get_file_info(pb)
            
                print(f"❌ 不同: {rel}")
                print(f"   {name_a}: {pa}\n      MD5: {md5_a}\n      Size: {size_a} bytes\n      Modified: {mtime_a}")
                print(f"   {name_b}: {pb}\n      MD5: {md5_b}\n      Size: {size_b} bytes\n      Modified: {mtime_b}")
        elif pa:
            print(f"⚠ 仅在 {name_a}: {rel}")
        else:
            print(f"⚠ 仅在 {name_b}: {rel}")

    print(f"==== ✅ 对比完成：{job_name} ({name_a} vs {name_b}) ====\n")

def main():
    # 不同工作区可能的配置文件路径
    possible_cfg_paths = [
        "./config.ini",
        "/Volumes/Data/SyncFolder/config.ini"
    ]

    cfg_path = None
    for path in possible_cfg_paths:
        if os.path.exists(path):
            cfg_path = path
            break

    if not cfg_path:
        print("❌ 找不到配置文件，退出")
        return

    print(f"🔹 使用配置文件: {cfg_path}")
    config = configparser.ConfigParser()
    config.optionxform = str  # 保留键名大小写
    config.read(cfg_path, encoding="utf-8")

    if not config.sections():
        print("❌ 配置文件无有效内容，退出")
        return

    for section in config.sections():
        ignore = config[section].get("ignore", "")
        rules = parse_ignore_rules(ignore)

        # 找出所有 folder_ 前缀的键
        folder_keys = [k for k in config[section] if k.startswith("folder_")]
        if len(folder_keys) != 2:
            print(f"\n==== ❌ Section '{section}' 必须恰好有两个 folder_ 开头的键，当前找到 {len(folder_keys)} 个，跳过该 section ====")
            continue

        name_a, name_b = folder_keys
        folder_a, folder_b = config[section][name_a], config[section][name_b]

        # 检查文件夹是否存在
        if not os.path.exists(folder_a):
            print(f"\n==== ❌ Section '{section}': 文件夹 {folder_a} 不存在，跳过该 section ====")
            continue
        if not os.path.exists(folder_b):
            print(f"\n==== ❌ Section '{section}': 文件夹 {folder_b} 不存在，跳过该 section ====")
            continue

        # 去掉前缀
        display_a = name_a[len("folder_"):]
        display_b = name_b[len("folder_"):]
        compare(folder_a, folder_b, display_a, display_b, rules, section)

if __name__ == "__main__":
    main()
