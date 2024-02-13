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
                self._logger.info("Converting diagram.")
                # Create a temporary file to hold the Mermaid code.
                with open(temporary_directory / f"diagram_{i + 1}.mmd") as mermaid_file:
                    # Write the Mermaid code to the file.
                    mermaid_code_unescaped = html_lib.unescape(mermaid_code)
                    mermaid_file.write(mermaid_code_unescaped.encode("utf-8"))
                    mermaid_file.flush()

                    # Create a filename for the image.
                    image_filename = str(temporary_directory / f"diagram_{i+1}.png")

                    # Convert the Mermaid diagram to an image using mmdc.
                    command = f"mmdc -i {mermaid_file.name} -o {image_filename} -b transparent -t dark --scale 4"

                    os.system(command)

                    # Replace the Mermaid code with the image in the HTML string.
                    image_html = f'<img src="file://{os.path.abspath(image_filename)}" alt="Mermaid diagram {i+1}">'
                    html = html.replace(f'<pre class="mermaid"><code>{mermaid_code}</code></pre>', image_html)

            self._logger.info(html)
            with open(temporary_directory / "post_mermaid_translation.html", "wb") as temp:
                temp.write(html.encode('utf-8'))

            self._logger.info("Rendering on `Headless Chrome`(execute JS).")
            with Popen([self._program_path,
                        '--disable-web-security',
                        '--no-sandbox',
                        '--headless',
                        '--disable-gpu',
                        '--disable-web-security',
                        '-–allow-file-access-from-files',
                        '--run-all-compositor-stages-before-draw',
                        '--virtual-time-budget=10000',
                        '--dump-dom',
                        temp.name], stdout=PIPE) as chrome:
                return chrome.stdout.read().decode('utf-8')

        except Exception as e:
            self._logger.error(f'Failed to render by JS: {e}')

        return html
