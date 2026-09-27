# Editing About

Edit `shaders/lang/en_us.lang` and copy the same text to `en_US.lang`.
Both files are provided because loader/resource-language casing can differ.

Change these entries as desired:

```
screen.ABOUT_VERSION=Version: 0.6.5 experimental
screen.ABOUT_OWNER=Owner: EDIT ME
screen.ABOUT_CONTACT=Contact: EDIT ME
screen.ABOUT_LICENSE=License: EDIT ME
screen.ABOUT_CREDITS=Credits: EDIT ME
screen.ABOUT_BUILD=Build: EDIT ME
```

Their `.comment` entries are the hover explanations. Preserve property keys and
change the text after `=`. These are labels, not shader options or editable input
boxes inside Minecraft. The supplied source license is in `LICENSE.txt`; editing
an About label does not modify that license file.

After editing, repack with `shaders/` at the ZIP root or run `build.py`.
