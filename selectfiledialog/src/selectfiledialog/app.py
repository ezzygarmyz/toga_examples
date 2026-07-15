
import os
import asyncio
import toga
from toga.style.pack import COLUMN, ROW, Pack

from java import dynamic_proxy, jclass, jarray
from android.net import Uri
from java.lang import Runnable, String
from androidx.activity.result import ActivityResultCallback
from org.beeware.android import MainActivity


class RunnableProxy(dynamic_proxy(Runnable)):
    def __init__(self, func):
        super().__init__()
        self.func = func
        
    def run(self):
        self.func()


class SelectFileCallback(dynamic_proxy(ActivityResultCallback)):
    def __init__(self, picker):
        super().__init__()
        self.picker = picker

    def onActivityResult(self, uri):
        if uri:
            self.picker._set_result(uri.toString())
        else:
            self.picker._set_result(None)


class SelectFileDialog:
    def __init__(self, activity):
        self.activity = activity
        self._future = None

        callback_proxy = SelectFileCallback(self)
        self._launcher = self.activity.registerForActivityResult(
            jclass("androidx.activity.result.contract.ActivityResultContracts$OpenDocument")(),
            callback_proxy
        )

    async def pick_file(self, mime_types=None):
        """
        :param mime_types: A list of MIME strings, e.g., ["image/*", "application/pdf"] 
                           Defaults to ["*/*"] (all files) if not specified.
        """
        if mime_types is None:
            mime_types = ["*/*"]

        self._future = asyncio.get_event_loop().create_future()
        java_mime_types = jarray(String)(mime_types)

        def launch_intent():
            self._launcher.launch(java_mime_types)

        self.activity.runOnUiThread(RunnableProxy(launch_intent))
        return await self._future
    
    def uri_to_path(self, uri_string):
        uri = Uri.parse(uri_string)
        OpenableColumns = jclass(
            "android.provider.OpenableColumns"
        )
        resolver = self.activity.getContentResolver()
        filename = "selected_file"
        cursor = resolver.query(
            uri,
            None,
            None,
            None,
            None
        )
        if cursor:
            try:
                if cursor.moveToFirst():
                    index = cursor.getColumnIndex(
                        OpenableColumns.DISPLAY_NAME
                    )
                    if index >= 0:
                        filename = cursor.getString(index)
            finally:
                cursor.close()

        input_stream = resolver.openInputStream(uri)
        target = os.path.join(
            str(self.activity.getCacheDir().getAbsolutePath()),
            filename
        )
        with open(target, "wb") as out:
            buffer = bytearray(8192)
            while True:
                chunk = input_stream.read(buffer)
                if chunk == -1:
                    break
                out.write(buffer[:chunk])
        input_stream.close()
        return target

    def _set_result(self, file_uri):
        if self._future and not self._future.done():
            self._future.set_result(file_uri)


class selectfileialogexample(toga.App):
    def startup(self):

        self.activity = MainActivity.singletonThis
        self.file_selector = SelectFileDialog(self.activity)

        select_button = toga.Button(
            text="Select File",
            on_press=self.on_select_click
        )
        self.path_label = toga.Label(
            text=""
        )
        main_box = toga.Box(
            style=Pack(
                direction=COLUMN,
                gap=10
            )
        )
        main_box.add(
            select_button,
            self.path_label
        )

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()


    async def on_select_click(self, button):
        self.path_label.text = ""
        uri = await self.file_selector.pick_file()
        if uri:
            path = self.file_selector.uri_to_path(uri)
            self.path_label.text = path


def main():
    return selectfileialogexample()
