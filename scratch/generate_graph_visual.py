import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.features.practice.langgraph.graph import interview_graph


def main():
    print("=== Extracting Mermaid ASCII / Syntax from Compiled LangGraph ===")
    mermaid_syntax = interview_graph.get_graph().draw_mermaid()
    print(mermaid_syntax)

    # Save mermaid string to file
    out_file = os.path.join(
        os.path.dirname(__file__), "..", "..", "docs", "generated_langgraph.mmd"
    )
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(mermaid_syntax)

    print(f"\nSaved Mermaid diagram to {out_file}")

    # Try saving PNG if grandalf / pygraphviz / pyppeteer / mermaid CLI installed
    try:
        png_data = interview_graph.get_graph().draw_mermaid_png()
        png_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "docs", "interview_graph.png"
        )
        with open(png_path, "wb") as f:
            f.write(png_data)
        print(f"Successfully generated graph PNG image at: {png_path}")
    except Exception as e:
        print(f"Note: PNG generation requires web/graphviz dependencies: {e}")


if __name__ == "__main__":
    main()
