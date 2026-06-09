from gui import AuthWindow, MainWindow

def main():
    auth_app = AuthWindow()
    auth_app.mainloop()

    if auth_app.authenticated_user_id:
        main_app = MainWindow(auth_app.authenticated_user_id)
        main_app.mainloop()

if __name__ == "__main__":
    main()