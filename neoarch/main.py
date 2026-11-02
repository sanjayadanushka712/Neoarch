"""
NeoArch - Entry point

A modern Arch Linux package management frontend.
"""

import os
import sys


def _parse_args(argv):
    """Return (start_minimized, error) for the supported CLI options."""
    minimized = False
    for arg in argv:
        if arg in ("--help", "-h"):
            print("NeoArch - Elevate Your Arch Experience")
            print("Usage: python -m neoarch [--minimized]")
            print("A graphical package manager for Arch Linux with AUR support.")
            print("  --minimized  Start hidden in the system tray.")
            return None, None
        if arg in ("--minimized", "--tray"):
            minimized = True
            continue
        return None, f"Unknown option: {arg}"
    return minimized, None


def main():
    minimized, error = _parse_args(sys.argv[1:])
    if error:
        print(error)
        print("Use --help for usage information.")
        sys.exit(1)
    if minimized is None:
        sys.exit(0)

    if os.geteuid() == 0:
        print("Do not run this application as root.")
        sys.exit(1)

    from PyQt6.QtWidgets import QApplication

    from neoarch.frontend.main_window import ArchPkgManagerUniGetUI
    from neoarch.resources.paths import APP_NAME

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    window = ArchPkgManagerUniGetUI()
    start_hidden = minimized or bool(
        window.settings.get('start_minimized', False))
    if start_hidden and window.tray_icon is not None:
        window.show_tray_notice()
        app.processEvents()
    else:
        window.show()

        # Make sure the very first mapped frame is complete (content + border
        # painted together) before the window manager fades the window in.
        app.processEvents()
        window.repaint()

    window.check_authentication_tools()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
