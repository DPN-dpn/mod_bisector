#!/usr/bin/env python3
import tkinter as tk
from ui import layout


def main():
    root = tk.Tk()
    root.title("mod-bisector")
    root.geometry("560x215")
    layout.build_ui(root)
    root.mainloop()


if __name__ == "__main__":
    main()

