import io
import zipfile
from unittest.mock import patch, MagicMock

import fonts


def _zip(names):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for n in names:
            zf.writestr(n, b"x")
    return buf.getvalue()


def test_install_extracts_only_regular_family_files_by_basename(tmp_path):
    data = _zip(["JetBrainsMonoNerdFont-Regular.ttf", "../evil/JetBrainsMonoNerdFont-Bold.ttf",
                 "JetBrainsMonoNerdFontPropo-Regular.ttf", "README.md"])
    resp = MagicMock(); resp.__enter__.return_value.read.return_value = data
    with patch("fonts.user_font_dir", return_value=tmp_path), \
         patch("fonts.urllib.request.urlopen", return_value=resp), \
         patch("fonts.sys.platform", "darwin"):
        fonts.install()
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "JetBrainsMonoNerdFont-Bold.ttf", "JetBrainsMonoNerdFont-Regular.ttf"]


def test_is_installed_detects_nerd_font(tmp_path):
    with patch("fonts._search_dirs", return_value=[tmp_path]):
        assert not fonts.is_installed()
        (tmp_path / "Foo NerdFont-Regular.ttf").write_bytes(b"x")
        assert fonts.is_installed()
