from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from pinleaf import metadata
from pinleaf.config import icon_path


def show_about(parent: Gtk.Window) -> None:
    comments = f"{metadata.APP_DESCRIPTION}\n\nBuild date: {metadata.BUILD_DATE}"
    developers = [metadata.MAINTAINER_NAME]
    copyright_text = "Copyright (c) 2026 Pinleaf contributors"

    if hasattr(Adw, "AboutDialog"):
        dialog = Adw.AboutDialog(
            application_name=metadata.APP_NAME,
            application_icon="pinleaf",
            version=metadata.APP_VERSION,
            developer_name=metadata.MAINTAINER_NAME,
            comments=comments,
            website=metadata.PROJECT_WEBSITE,
            issue_url="",
            license_type=Gtk.License.MIT_X11,
            copyright=copyright_text,
            developers=developers,
            artists=[metadata.FONT_CREDIT],
        )
        dialog.add_link(metadata.MAINTAINER_NAME, metadata.MAINTAINER_WEBSITE)
        dialog.present(parent)
        return

    window = Adw.AboutWindow(
        transient_for=parent,
        application_name=metadata.APP_NAME,
        application_icon="pinleaf",
        version=metadata.APP_VERSION,
        developer_name=metadata.MAINTAINER_NAME,
        comments=comments,
        website=metadata.PROJECT_WEBSITE,
        license_type=Gtk.License.MIT_X11,
        copyright=copyright_text,
        developers=developers,
        artists=[metadata.FONT_CREDIT],
    )
    window.add_link(metadata.MAINTAINER_NAME, metadata.MAINTAINER_WEBSITE)
    window.set_icon_from_file(str(icon_path(64)))
    window.present()
