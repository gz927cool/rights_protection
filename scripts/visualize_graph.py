"""
LangGraph Agent 结构可视化脚本

生成当前九步咨询系统的 Agent 结构图（Mermaid PNG 格式）

使用方法:
    python scripts/visualize_graph.py
    python scripts/visualize_graph.py --format svg
    python scripts/visualize_graph.py --xray
"""
import argparse
import os
from pathlib import Path


# 添加项目根目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph_model.consultation_graph import get_consultation_graph


def save_graph_image(graph, output_path: str, xray: bool = False):
    """将图结构保存为 PNG 图片"""
    g = graph.get_graph(xray=xray)

    # 生成 PNG
    png_data = g.draw_mermaid_png()

    with open(output_path, "wb") as f:
        f.write(png_data)

    print(f"✅ PNG 图片已保存: {output_path}")
    return output_path


def save_graph_mermaid(graph, output_path: str, xray: bool = False):
    """将图结构保存为 Mermaid 文本"""
    g = graph.get_graph(xray=xray)

    mermaid_text = g.draw_mermaid()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(mermaid_text)

    print(f"✅ Mermaid 图表已保存: {output_path}")
    return output_path


def print_graph_ascii(graph, xray: bool = False):
    """打印 ASCII 格式的图结构"""
    g = graph.get_graph(xray=xray)

    print("\n" + "=" * 60)
    print("📊 Agent 结构概览")
    print("=" * 60)

    # 获取节点信息
    nodes = list(g.nodes)
    print(f"\n节点数量: {len(nodes)}")
    print("\n节点列表:")
    for i, node in enumerate(nodes, 1):
        print(f"  {i}. {node}")

    # 打印边关系
    print("\n边关系:")
    for edge in g.edges:
        print(f"  {edge.source} → {edge.target}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="LangGraph Agent 可视化工具")
    parser.add_argument("--format", choices=["png", "mermaid", "both", "ascii"],
                        default="both", help="输出格式")
    parser.add_argument("--output", "-o", default="outputs/agent_graph",
                        help="输出文件路径(不含扩展名)")
    parser.add_argument("--xray", action="store_true",
                        help="显示更详细的内部结构")
    args = parser.parse_args()

    # 确保输出目录存在
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载图
    print("📦 加载 Agent 图结构...")
    graph = get_consultation_graph()
    print("✅ 图加载成功\n")

    base_path = args.output

    # 生成输出
    if args.format in ("png", "both"):
        png_path = f"{base_path}.png"
        save_graph_image(graph, png_path, xray=args.xray)

    if args.format in ("mermaid", "both"):
        mm_path = f"{base_path}.mmd"
        save_graph_mermaid(graph, mm_path, xray=args.xray)

    if args.format == "ascii":
        print_graph_ascii(graph, xray=args.xray)

    # 同时打印基本信息
    print_graph_ascii(graph, xray=args.xray)

    print("\n💡 提示:")
    print("   - PNG 文件可用浏览器打开查看")
    print("   - Mermaid 文件可在 https://mermaid.live 查看")
    print("   - 添加 --xray 参数可查看更详细的内部结构")


if __name__ == "__main__":
    main()
