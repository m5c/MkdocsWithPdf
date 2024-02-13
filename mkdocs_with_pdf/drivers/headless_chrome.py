import os
import html as html_lib
from logging import Logger
from shutil import which
from subprocess import PIPE, Popen
import re
import pathlib


class HeadlessChromeDriver(object):
    """ 'Headless Chrome' executor """

    @classmethod
    def setup(self, program_path: str, logger: Logger):
        if not which(program_path):
            raise RuntimeError(
                'No such `Headless Chrome` program or not executable'
                + f': "{program_path}".')
        return self(program_path, logger)

    def __init__(self, program_path: str, logger: Logger):
        self._program_path = program_path
        self._logger = logger

    def render(self, html: str, temporary_directory: pathlib.Path) -> str:
        try:
            mermaid_regex = r'<pre class="mermaid"><code>(.*?)</code></pre>'
            mermaid_matches = re.findall(mermaid_regex, html, flags=re.DOTALL)

            # Convert each Mermaid diagram to an image.
            for i, mermaid_code in enumerate(mermaid_matches):
                self._logger.info(f"Converting mermaid diagram {i}")

                # Create a temporary file to hold the Mermaid code.
                mermaid_file_path = temporary_directory / f"diagram_{i + 1}.mmd"
                with open(mermaid_file_path, "wb") as mermaid_file:
                    mermaid_code_unescaped = html_lib.unescape(mermaid_code)
                    mermaid_file.write(mermaid_code_unescaped.encode("utf-8"))

                # Create a filename for the image.
                image_file_path = temporary_directory / f"diagram_{i + 1}.png"

                # Convert the Mermaid diagram to an image using mmdc.
                command = f"mmdc -i {mermaid_file_path} -o {image_file_path} -b transparent -t dark --scale 4 --quiet"

                os.system(command)

                # Replace the Mermaid code with the image in the HTML string.
                image_html = f'<img src="file://{image_file_path}" alt="Mermaid diagram {i+1}">'
                html = html.replace(f'<pre class="mermaid"><code>{mermaid_code}</code></pre>', image_html)

            self._logger.info(f"Post mermaid translation: {html}")
            with open(temporary_directory / "post_mermaid_translation.html", "wb") as temp:
                temp.write(html.encode('utf-8'))

            self._logger.info("Rendering on `Headless Chrome`(execute JS).")
            with Popen([self._program_path,
                        '--disable-web-security',
                        '--headless',
                        '--disable-gpu',
                        '--disable-web-security',
                        '-–allow-file-access-from-files',
                        '--run-all-compositor-stages-before-draw',
                        '--virtual-time-budget=10000',
                        '--dump-dom',
                        temp.name], stdout=PIPE) as chrome:
                chrome_output = chrome.stdout.read().decode('utf-8')
                self._logger.info(f"Post chrome translation: {chrome_output}")
                return chrome_output

        except Exception as e:
            self._logger.error(f'Failed to render by JS: {e}')

        return html
