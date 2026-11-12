"""Backend helpers shared by the optional kernel timing builder."""
import re
import shlex


def haskell_strictness(source):
    """Derive structural forcing only; retain the untouched export alongside it."""
    source = '{-# LANGUAGE DeriveGeneric, DeriveAnyClass #-}\n' + source
    source = source.replace('import qualified Prelude;',
        'import qualified Prelude;\nimport qualified GHC.Generics;\nimport qualified Control.DeepSeq;')
    return re.sub(r'((?:^|\n)(?:data|newtype)\s+[^;]+);',
                  r'\1 deriving (GHC.Generics.Generic, Control.DeepSeq.NFData);', source)

def shell_launcher(path,argv):
    path.write_text('#!/bin/sh\nexec '+shlex.join(map(str,argv))+' "$@"\n');path.chmod(0o755)
