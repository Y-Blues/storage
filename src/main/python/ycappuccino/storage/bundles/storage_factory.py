# app="all"
from pelix.ipopo.constants import use_ipopo

from ycappuccino.api.core import IActivityLogger, IConfiguration
import logging
from pelix.ipopo.decorators import (
    ComponentFactory,
    Requires,
    Validate,
    Invalidate,
    Provides,
    Instantiate,
)

from ycappuccino.api.proxy import YCappuccinoRemote
from ycappuccino.api.storage import IStorageFactory
from ycappuccino.core.decorator_app import Layer

from ycappuccino.core.framework import Framework

_logger = logging.getLogger(__name__)


@ComponentFactory("storageFactory-Factory")
@Provides(
    specifications=[YCappuccinoRemote.__name__, IStorageFactory.__name__],
    controller="_available",
)
@Requires("_log", IActivityLogger.__name__, spec_filter="'(name=main)'")
@Requires("_config", IConfiguration.__name__)
@Instantiate("storageFactory")
@Layer(name="ycappuccino_storage")
class MongoStorageFactory(IStorageFactory):

    def __init__(self):
        super(IStorageFactory, self).__init__()
        self._log = None

    @Validate
    def validate(self, context):
        self._log.info("storageFactory validating")
        prop_layer = Framework.get_instance().get_layer_properties(
            "ycappuccino_storage"
        )
        if "type" in prop_layer.keys():
            type = prop_layer["type"]
            if type == "mongo":
                with use_ipopo(context) as ipopo:
                    ipopo.instantiate("MongoStorage-Factory", "MongoStorage", {})
        self._log.info("storageFactory validated")

    @Invalidate
    def invalidate(self, context):
        self._log.info("storageFactory invalidating")

        self._log.info("storageFactory invalidated")
