import os
import shutil
import random
from redeclipse.textures.basetex import Sky, Default


comment = """
// {map_name} by {author} (maps/base)
// Config generated by Red Eclipse Map Generator

// Variables stored in map file, may be uncommented here, or changed from editmode.
"""

class TextureManager:
    def __init__(self):
        self.atlas = {}
        self.atlas_backref = {}
        self.texref = {}
        # Init
        self.discover_textures()
        self.get('sky')
        self.get('default')

    def discover_textures(self):
        self.texref['sky'] = Sky
        self.texref['default'] = Default

    def get(self, name):
        if name not in self.atlas_backref:
            # Insert tex
            tex = self.texref[name]
            pos = len(self.atlas)
            self.atlas[pos] = tex
            # Now insert backref
            self.atlas_backref[name] = pos
        return self.atlas_backref[name]

    def random(self):
        return self.get(random.choice([
            'gold', 'admin', 'stone', 'dirt', 'wood'
        ]))

    def emit_conf(self, map_output_path, author="Python", map_name="test", ):
        filename = map_output_path.name.replace('.mpz', '.cfg')
        handle = open(filename, 'w')
        handle.write(comment.format(author=author, map_name=map_name))
        for idx, (tex_key, tex) in enumerate(self.atlas.items()):
            handle.write(tex.conf(tex, idx=idx))
        handle.close()

    def copy_data(self):
        outdir = "/home/hxr/games/redeclipse-1.5.3/data/hxr/textures/"
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        for idx, (tex_key, tex) in enumerate(self.atlas.items()):
            if not hasattr(tex, 'files'):
                continue

            for texfile in tex.files(tex):
                shutil.copy(
                    os.path.join(os.path.dirname(os.path.realpath(__file__)), tex.srcpath, texfile),
                    os.path.join(outdir, texfile)
                )


class ThemedTextureManager(TextureManager):

    def get_c(self, category):
        if category == 'generic':
            return self.get(random.choice(self.theme.GenericMaterial))
        elif category == 'column':
            return self.get(random.choice(self.theme.ColumnMaterial))
        elif category == 'floor':
            return self.get(random.choice(self.theme.FloorMaterial))
        elif category == 'wall':
            return self.get(random.choice(self.theme.WallMaterial))
        elif category == 'accent':
            return self.get(random.choice(self.theme.AccentMaterial))

        return random.choice(self.theme.GenericMaterial)

    def discover_textures(self):
        super().discover_textures()
        for cls in dir(self.textures):
            mod = getattr(self.textures, cls)
            if 'type' in str(type(mod)):
                if any(['redeclipse.textures.' in str(c) for c in mod.__bases__]):
                    self.texref[cls.lower()] = mod


class MinecraftThemedTextureManager(ThemedTextureManager):
    from redeclipse.textures import minecraft, minecraft_theme
    textures = minecraft
    theme = minecraft_theme


class DefaultThemedTextureManager(ThemedTextureManager):
    from redeclipse.textures import dull, dull_theme
    textures = dull
    theme = dull_theme

class PaperThemedTextureManager(ThemedTextureManager):
    from redeclipse.textures import paper, paper_theme
    textures = paper
    theme = paper_theme

class PrimaryThemedTextureManager(ThemedTextureManager):
    from redeclipse.textures import primary, primary_theme
    textures = primary
    theme = primary_theme
