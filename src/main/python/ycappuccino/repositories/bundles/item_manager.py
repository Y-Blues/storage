"""
component that manage model orm list
"""

from ycappuccino_api.core.api import IActivityLogger, IConfiguration
from src.main.python.proxy import YCappuccinoRemote
from ycappuccino_storage import AbsManager
from ycappuccino_api.storage.api import (
    IItemManager,
    IStorage,
    IManager,
    IDefaultManager,
    IUploadManager,
)
import logging
from pelix.ipopo.decorators import (
    ComponentFactory,
    Requires,
    Validate,
    Invalidate,
    Property,
    Provides,
    Instantiate,
    BindField,
    UnbindField,
)
from src.main.python.decorator_app import Layer
from src.main.python import decorators
import ycappuccino_core.framework as framework


_logger = logging.getLogger(__name__)


@ComponentFactory("ItemManager-Factory")
@Provides(specifications=[YCappuccinoRemote.__name__, IItemManager.__name__])
@Requires("_log", IActivityLogger.__name__, spec_filter="'(name=main)'")
@Requires("_storage", IStorage.__name__, optional=True)
@Requires("_config", IConfiguration.__name__)
@Property("_is_secure", "secure", True)
@Requires("_managers", specification=IManager.__name__, aggregate=True, optional=True)
@Requires("_default_manager", specification=IDefaultManager.__name__)
@Requires("_upload_manager", specification=IUploadManager.__name__)
@Instantiate("itemManager")
@Layer(name="ycappuccino_storage")
class ItemManager(IItemManager, AbsManager):

    def __init__(self):
        super(ItemManager, self).__init__()
        super(AbsManager, self).__init__()
        self._log = None
        self._config = None
        self._storage = None
        self._managers = None
        self._map_managers = {}
        self._upload_manager = None
        self._default_manager = None
        self._context = None

    def get_one(self, a_item_id, a_id, a_params=None, a_subject=None):
        """ """
        w_dicts = decorators.get_map_items_emdpoint()
        if a_id in w_dicts:
            w_result = w_dicts[a_id]
        return w_result

    def get_aggregate_one(self, a_item_id, a_id, a_params=None, a_subject=None):
        """ """
        return self.get_one(a_item_id, a_id, a_params, a_subject)

    def get_many(self, a_item_id, a_params=None, a_subject=None):
        w_result = decorators.get_map_items_emdpoint()

        return w_result

    def get_aggregate_many(self, a_item_id, a_params=None, a_subject=None):

        return self.get_many(a_item_id, a_params, a_subject)

    def get_item_from_id_plural(self, a_item_plural):
        """return list of item id"""
        return {"id": "item", "secureRead": False}

    @BindField("_managers")
    def bind_manager(self, field, a_manager, a_service_reference):
        self._context = a_service_reference._ServiceReference__bundle._Bundle__context
        for w_item_id in a_manager.get_item_ids():
            if w_item_id not in self._map_managers:
                self._map_managers[w_item_id] = a_manager

    @BindField("_default_manager")
    def bind_default_manager(self, field, a_manager, a_service_reference):
        self._context = a_service_reference._ServiceReference__bundle._Bundle__context
        self._default_manager = a_manager
        for w_item_id in a_manager.get_item_ids():
            w_item = decorators.get_item(w_item_id)
            self._default_manager.add_item(w_item, self._context)

    @BindField("_upload_manager")
    def bind_upload_manager(self, field, a_manager, a_service_reference):
        self._context = a_service_reference._ServiceReference__bundle._Bundle__context
        self._upload_manager = a_manager
        for w_item_id in a_manager.get_item_ids():
            w_item = decorators.get_item(w_item_id)
            if w_item["multipart"]:
                self._upload_manager.add_item(w_item, self._context)

    @UnbindField("_default_manager")
    def unbind_default_manager(self, field, a_manager, a_service_reference):
        self._default_manager = None

    @UnbindField("_upload_manager")
    def unbind_upload_manager(self, field, a_manager, a_service_reference):
        self._upload_manager = None

    @UnbindField("_managers")
    def unbind_manager(self, field, a_manager, a_service_reference):

        for w_item_id in a_manager.get_item_ids():
            self._map_managers[w_item_id] = None

    def load_items(self):
        """ """
        """ load all item readed by framework item to be manage and add to link manager to be manage"""
        for w_item in decorators.get_map_items():
            self.load_item(w_item)

    def load_item(self, a_item):
        """load item to be manage and add to link manager to be manage"""
        if "id" in a_item.keys() and a_item["id"] not in self._map_managers:
            # instanciate a component regarding the manager factory to use by item and default manage can be multi item
            if not a_item["abstract"] and self._default_manager is not None:
                self._log.info("add item {}".format(a_item["id"]))
                self._default_manager.add_item(a_item, self._context)
                if a_item["multipart"] and self._upload_manager is not None:
                    self._upload_manager.add_item(a_item, self._context)

        else:
            print("error")

    @Validate
    def validate(self, context):
        self._log.info("Manager validating")
        try:
            self._context = context
            framework.set_item_manager(self)
        except Exception as e:
            self._log.error("Manager Error {}".format(e))
            self._log.exception(e)

        self._log.info("Manager validated")

    @Invalidate
    def invalidate(self, context):
        self._log.info("Manager invalidating")

        self._log.info("Manager invalidated")
