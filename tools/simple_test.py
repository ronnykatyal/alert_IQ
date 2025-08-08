# gui/simple_test.py - Simple GUI test

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tkinter as tk
from tkinter import messagebox

def test_basic_gui():
    """Test basic GUI functionality"""
    try:
        print("🧪 Testing basic GUI...")
        
        root = tk.Tk()
        root.title("Alert_IQ Test")
        root.geometry("400x300")
        
        # Test label creation
        label = tk.Label(root, text="Alert_IQ Test Window", font=("Arial", 16))
        label.pack(pady=20)
        
        # Test button
        def show_message():
            messagebox.showinfo("Test", "GUI is working!")
        
        button = tk.Button(root, text="Test Button", command=show_message)
        button.pack(pady=10)
        
        # Test frame
        frame = tk.Frame(root, bg="lightgray", relief="raised", bd=2)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        inner_label = tk.Label(frame, text="If you see this, basic GUI works!", bg="lightgray")
        inner_label.pack(pady=20)
        
        print("✅ Basic GUI test successful - window should appear")
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Basic GUI test failed: {e}")
        return False

if __name__ == "__main__":
    test_basic_gui()