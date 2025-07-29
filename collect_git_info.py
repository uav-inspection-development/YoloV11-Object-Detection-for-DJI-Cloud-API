#!/usr/bin/env python3
"""
Git信息收集脚本
在PyInstaller打包时自动收集Git提交记录信息
"""

import os
import subprocess
import json
from datetime import datetime


def run_git_command(command):
    """
    执行Git命令并返回结果

    Args:
        command (str): Git命令

    Returns:
        str: 命令输出结果，如果出错返回None
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Git命令执行失败: {command}")
            print(f"错误信息: {result.stderr}")
            return None
    except Exception as e:
        print(f"执行Git命令时发生异常: {e}")
        return None


def get_git_info():
    """
    获取Git仓库信息

    Returns:
        dict: 包含Git信息的字典
    """
    git_info = {
        "available": False,
        "commit_hash": "未知",
        "commit_hash_short": "未知",
        "commit_message": "未知",
        "commit_author": "未知",
        "commit_email": "未知",
        "commit_date": "未知",
        "branch": "未知",
        "tag": "未知",
        "total_commits": 0,
        "repository_url": "未知"
    }

    # 检查是否为Git仓库
    if not run_git_command("git rev-parse --git-dir"):
        print("警告: 当前目录不是Git仓库")
        return git_info

    git_info["available"] = True

    # 获取最新提交的哈希值
    commit_hash = run_git_command("git rev-parse HEAD")
    if commit_hash:
        git_info["commit_hash"] = commit_hash
        git_info["commit_hash_short"] = commit_hash[:8]

    # 获取最新提交信息
    commit_message = run_git_command("git log -1 --pretty=format:%s")
    if commit_message:
        git_info["commit_message"] = commit_message

    # 获取提交作者
    commit_author = run_git_command("git log -1 --pretty=format:%an")
    if commit_author:
        git_info["commit_author"] = commit_author

    # 获取提交作者邮箱
    commit_email = run_git_command("git log -1 --pretty=format:%ae")
    if commit_email:
        git_info["commit_email"] = commit_email

    # 获取提交日期
    commit_date = run_git_command("git log -1 --pretty=format:%ci")
    if commit_date:
        git_info["commit_date"] = commit_date

    # 获取当前分支
    branch = run_git_command("git rev-parse --abbrev-ref HEAD")
    if branch:
        git_info["branch"] = branch

    # 获取最新标签
    tag = run_git_command("git describe --tags --abbrev=0")
    if tag:
        git_info["tag"] = tag

    # 获取提交总数
    total_commits = run_git_command("git rev-list --count HEAD")
    if total_commits and total_commits.isdigit():
        git_info["total_commits"] = int(total_commits)

    # 获取远程仓库URL
    repo_url = run_git_command("git config --get remote.origin.url")
    if repo_url:
        git_info["repository_url"] = repo_url

    return git_info


def save_git_info_to_file(output_file="git_info.json"):
    """
    将Git信息保存到JSON文件

    Args:
        output_file (str): 输出文件路径
    """
    git_info = get_git_info()

    # 添加构建时间
    git_info["build_time"] = datetime.now().isoformat()

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(git_info, f, ensure_ascii=False, indent=2)
        print(f"Git信息已保存到: {output_file}")
        return True
    except Exception as e:
        print(f"保存Git信息失败: {e}")
        return False


def generate_git_info_python_file(output_file="git_info.py"):
    """
    生成包含Git信息的Python文件

    Args:
        output_file (str): 输出Python文件路径
    """
    git_info = get_git_info()
    git_info["build_time"] = datetime.now().isoformat()

    python_content = f'''"""
自动生成的Git信息文件
构建时间: {git_info["build_time"]}
"""

# Git仓库信息
GIT_INFO = {repr(git_info)}

def get_git_info():
    """获取Git信息"""
    return GIT_INFO

def format_git_info_for_about():
    """格式化Git信息用于关于页面显示"""
    info = GIT_INFO

    if not info.get("available", False):
        return "### 版本信息\\n未找到Git仓库信息"

    # 使用字符串拼接而不是f-string来避免嵌套问题
    lines = []
    lines.append("### 📊 版本信息")
    lines.append("- **版本标签**: " + str(info.get('tag', '未知')))
    lines.append("- **提交哈希**: `" + str(info.get('commit_hash_short', '未知')) + "`")
    lines.append("- **分支**: " + str(info.get('branch', '未知')))
    lines.append("")
    lines.append("### 📝 最新提交")
    lines.append("- **提交信息**: " + str(info.get('commit_message', '未知')))
    lines.append("- **提交作者**: " + str(info.get('commit_author', '未知')) + " <" + str(info.get('commit_email', '未知')) + ">")
    lines.append("- **提交日期**: " + str(info.get('commit_date', '未知')))
    lines.append("")
    lines.append("### 🏗️ 构建信息")
    lines.append("- **构建时间**: " + str(info.get('build_time', '未知')))
    lines.append("- **总提交数**: " + str(info.get('total_commits', 0)))
    lines.append("- **仓库地址**: " + str(info.get('repository_url', '未知')))

    return "\\n".join(lines)

def get_version_string():
    """获取简短的版本字符串"""
    info = GIT_INFO
    if info.get("available", False):
        tag = info.get('tag', '')
        commit_short = info.get('commit_hash_short', '')
        if tag and tag != '未知':
            return tag + " (" + commit_short + ")"
        elif commit_short and commit_short != '未知':
            return "dev-" + commit_short
    return "未知版本"
'''

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(python_content)
        print(f"Git信息Python文件已生成: {output_file}")
        return True
    except Exception as e:
        print(f"生成Git信息Python文件失败: {e}")
        return False


def print_git_info():
    """打印Git信息到控制台"""
    git_info = get_git_info()

    print("=" * 50)
    print("Git 仓库信息")
    print("=" * 50)

    if not git_info["available"]:
        print("× 未找到Git仓库")
        return

    print("√ Git仓库可用")
    print(f"* 最新提交: {git_info['commit_message']}")
    print(f"* 提交作者: {git_info['commit_author']} <{git_info['commit_email']}>")
    print(f"* 提交日期: {git_info['commit_date']}")
    print(f"* 提交哈希: {git_info['commit_hash_short']}")
    print(f"* 当前分支: {git_info['branch']}")
    print(f"* 最新标签: {git_info['tag']}")
    print(f"* 总提交数: {git_info['total_commits']}")
    print(f"* 仓库地址: {git_info['repository_url']}")
    print("=" * 50)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Git信息收集工具")
    parser.add_argument("--json", help="保存为JSON文件", metavar="FILENAME")
    parser.add_argument("--python", help="生成Python文件", metavar="FILENAME")
    parser.add_argument("--print", action="store_true", help="打印Git信息")

    args = parser.parse_args()

    if args.json:
        save_git_info_to_file(args.json)
    elif args.python:
        generate_git_info_python_file(args.python)
    elif args.print:
        print_git_info()
    else:
        # 默认行为：生成Python文件
        generate_git_info_python_file("git_info.py")
        print_git_info()
