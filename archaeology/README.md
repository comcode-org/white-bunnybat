This directory holds the various TTF files that are the "raw" input to our current endeavour.

There are also some Python scripts:

- ttf_to_sfd.py (convert .ttf to fontforge .sfd programatically)
- diff.py (diff two fonts, .ttf or .sfd or whatever)

So far the results look reasonable.

Note: the website font (website.ttf) has different global font metrics. This seems related to a recent complaint by southr6.

Also, Kaj's font (kaj.ttf / kaj2.sfd) has different corruption chars -- besides other known and correctly reported differences. This seems to be related to fixing the "self-intersection" errors these characters have in the current .ttf. I still don't know how Kaj "fixed" these errors. Probably we don't care about this for now.

UPDATE: actually, diff.py seems to fail to compare dafont.ttf to game.ttf. Almost all characters show differences. I only wanted to do this comparison for archaeological purposes anyway, though.
