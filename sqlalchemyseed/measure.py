"""Check whether sqlalchemyseed generates values or only loads the ones you give it."""

import pathlib
import re

import sqlalchemyseed


def main() -> None:
    public = sorted(name for name in dir(sqlalchemyseed) if not name.startswith("_"))
    print("public API:", ", ".join(public))
    loaders = [name for name in public if name.startswith("load_entities_from_")]
    print("loaders:", ", ".join(loaders))
    assert loaders == ["load_entities_from_csv", "load_entities_from_json", "load_entities_from_yaml"]

    package = pathlib.Path(sqlalchemyseed.__file__).parent
    generating = [
        f"{path.relative_to(package)}:{number}"
        for path in package.rglob("*.py")
        for number, line in enumerate(path.read_text().splitlines(), start=1)
        if re.search(r"^\s*(import|from)\s+(faker|random|mimesis)\b", line)
    ]
    print("imports of faker, random or mimesis:", generating or "none")
    assert not generating


if __name__ == "__main__":
    main()
