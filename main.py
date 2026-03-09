import tkinter as tk
from chat_ui import ChatUI

def main():
    root=tk.Tk()
    app=ChatUI(root)
    root.mainloop()

if __name__ =="__main__":
    main()