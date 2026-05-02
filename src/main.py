import tkinter as tk
from app.PetriNetEditor import PetriNetEditor


if __name__ == "__main__":
    root = tk.Tk()
    app = PetriNetEditor(root)
    root.mainloop()