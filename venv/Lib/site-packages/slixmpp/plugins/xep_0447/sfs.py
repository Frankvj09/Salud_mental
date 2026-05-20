import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, Literal

from slixmpp.plugins import BasePlugin
from slixmpp.stanza import Message
from slixmpp.xmlstream import register_stanza_plugin

from . import stanza

log = logging.getLogger(__name__)


class XEP_0447(BasePlugin):

    """
    XEP-0447: Stateless File Sharing

    Only support outgoing SFS, incoming is not handled at all.
    """

    name = "xep_0447"
    description = "XEP-0447: Stateless File Sharing"
    dependencies = {"xep_0300", "xep_0446"}
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Message, stanza.StatelessFileSharing)

        register_stanza_plugin(stanza.StatelessFileSharing, stanza.Sources)
        register_stanza_plugin(
            stanza.StatelessFileSharing, self.xmpp["xep_0446"].stanza.File
        )
        register_stanza_plugin(stanza.Sources, stanza.UrlData, iterable=True)

    def get_sfs(
        self,
        path: Path,
        uris: Iterable[str] | None = None,
        media_type: str | None = None,
        desc: str | None = None,
        disposition: Literal["inline", "attachment"] | None = None
    ) -> stanza.StatelessFileSharing:
        """
        Produce an SFS element from a file present locally.

        :param path: Path of the file.
        :param uris: Iterable on uris to that file.
        :param media_type: Media type of the file.
        :param desc: Description of the file.
        :param disposition: The content-disposition of the file.
        :returns: The SFS element.
        """
        sfs = stanza.StatelessFileSharing()
        if disposition:
            sfs["disposition"] = disposition
        if uris is not None:
            for uri in uris:
                ref = stanza.UrlData()
                ref["target"] = uri
                sfs["sources"].append(ref)
        if media_type:
            sfs["file"]["media-type"] = media_type
        if desc:
            sfs["file"]["desc"] = desc
        sfs["file"]["name"] = path.name

        stat = path.stat()
        sfs["file"]["size"] = stat.st_size
        sfs["file"]["date"] = datetime.fromtimestamp(stat.st_mtime)

        h = self.xmpp.plugin["xep_0300"].compute_hash(path)
        h["value"] = h["value"].decode()
        sfs["file"].append(h)

        return sfs
