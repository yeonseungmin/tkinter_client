
import tkinter as tk
from chat_ui import ChatUI

def main() -> None:
    root=tk.Tk()
    ChatUI(root)
    root.mainloop()
    
if __name__ == "__main__":
    main()