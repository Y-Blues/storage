# app="all"
from ycappuccino.api.core import IActivityLogger, IConfiguration
from ycappuccino.api.models import create_item
from ycappuccino.api.proxy import YCappuccinoRemote
from ycappuccino.api.storage import IStorage
import logging
from pelix.ipopo.decorators import (
    ComponentFactory,
    Requires,
    Validate,
    Invalidate,
    Provides,
)
from pymongo import MongoClient
import time

from uuid import uuid4
import json
from ycappuccino.core.decorator_app import Layer

from ycappuccino.core.executor_service import Callable

from ycappuccino.core import executor_service

from ycappuccino.core.framework import Framework

_logger = logging.getLogger(__name__)


class ValidateStorageConnect(Callable):
    """ """

    def __init__(self, a_service):
        super(ValidateStorageConnect, self).__init__("validateStorageConnect")
        self._service = a_service

    def run(self):
        self._service.validateConnect()


@ComponentFactory("MongoStorage-Factory")
@Provides(
    specifications=[YCappuccinoRemote.__name__, IStorage.__name__],
    controller="_available",
)
@Requires("_log", IActivityLogger.__name__, spec_filter="'(name=main)'")
@Requires("_config", IConfiguration.__name__)
@Layer(name="ycappuccino_storage")
class MongoStorage(IStorage):

    def __init__(self):
        super(IStorage, self).__init__()
        self._log = None
        self._client = None
        self._db = None
        self._config = None
        self._host = None
        self._port = None
        self._username = None
        self._password = None
        self._db_name = None
        self._available = False

    def load_configuration(self):
        prop_layer = Framework.get_instance().get_layer_properties(
            "ycappuccino_storage"
        )
        self._host = "host" in prop_layer.keys() if prop_layer["host"] else None
        self._port = "port" in prop_layer.keys() if prop_layer["port"] else None
        self._username = (
            "username" in prop_layer.keys() if prop_layer["username"] else None
        )
        self._password = (
            "password" in prop_layer.keys() if prop_layer["password"] else None
        )
        self._db_name = (
            "db_name" in prop_layer.keys() if prop_layer["db_name"] else None
        )

    def aggregate(self, a_collection, a_pipeline):
        """aggegate data regarding filter and pipeline"""
        return self._db[a_collection].aggregate(a_pipeline)

    def get_one(self, a_collection, a_filter, a_params=None):
        """get dict identify by a Id"""
        return self._db[a_collection].find(a_filter)

    def get_many(self, a_collection, a_filter, a_offset, a_limit, a_sort):
        """return iterable of dict regarding filter"""
        w_offset = 0
        w_limit = 50
        w_sort = {"_cat": -1}

        if a_offset is not None:
            w_offset = a_offset
        if a_limit is not None:
            w_limit = a_limit
        if a_sort is not None:
            w_sort = json.loads(a_sort)

        w_res = self._db[a_collection].find(a_filter)
        w_res = w_res.sort(w_sort.items())
        w_res = w_res.skip(w_offset)
        w_res = w_res.limit(w_limit)

        return w_res

    def up_sert(self, a_item, a_id, a_new_dict):
        """ " update or insert new dict"""

        w_filter = {"_id": a_id, "_item_id": a_item["id"]}

        res = self._db[a_item["collection"]].find(w_filter)
        count = self._db[a_item["collection"]].count_documents(w_filter)

        if res != None and count != 0:
            model = create_item(a_item, res[0])
            model._mongo_model = res[0]

            if "_mongo_model" in a_new_dict:
                a_new_dict["_mongo_model"]["_mat"] = time.time()
                a_new_dict["_mongo_model"]["_item_id"] = a_item["id"]

                w_update = {"$set": a_new_dict["_mongo_model"]}
                model.update(a_new_dict)
            else:
                a_new_dict["_mat"] = time.time()
                a_new_dict["_item_id"] = a_item["id"]

                w_update = {"$set": a_new_dict}
                model.update(a_new_dict)
            if "_id" in w_update["$set"].keys():
                del w_update["$set"]["_id"]
            return self._db[a_item["collection"]].update_one(
                w_filter, w_update, upsert=True
            )
        else:
            if "_mongo_model" in a_new_dict:
                a_new_dict["_mongo_model"]["_cat"] = time.time()
                a_new_dict["_mongo_model"]["_mat"] = a_new_dict["_mongo_model"]["_cat"]
                a_new_dict["_mongo_model"]["_item_id"] = a_item["id"]
                a_new_dict["_mongo_model"]["_id"] = a_id

                w_update = a_new_dict["_mongo_model"]

            else:
                a_new_dict["_id"] = a_id
                a_new_dict["_mat"] = time.time()
                a_new_dict["_cat"] = a_new_dict["_mat"]
                a_new_dict["_item_id"] = a_item["id"]

                w_update = a_new_dict
            if "_id" not in w_update:
                w_update["id"] = uuid4().__str__()

            return self._db[a_item["collection"]].insert_one(w_update)

    def up_sert_many(self, a_collection, a_filter, a_new_dict):
        """update or insert document with new dict regarding filter"""
        if "_mongo_model" not in a_new_dict:
            a_new_dict["_mongo_model"] = {}
        a_new_dict["_mongo_model"]["_mat"] = time.time()
        if "_mongo_model" in a_new_dict:

            w_update = {"$set": a_new_dict["_mongo_model"]}
        else:
            w_update = {"$set": a_new_dict}
        return self._db[a_collection].update_many(a_filter, w_update, upsert=True)

    def delete(self, a_collection, a_id):
        """delete document identified by id if it exists"""
        w_filter = {"_id": a_id}
        self._db[a_collection].delete_one(w_filter, upsert=True)

    def delete_many(self, a_collection, a_filter):
        self._db[a_collection].delete_many(a_filter, upsert=True)

    def validateConnect(self):
        """ """
        try:
            self._client.server_info()
            self._available = True
        except Exception as e:
            self._available = False

    @Validate
    def validate(self, context):
        self._log.info("MongoStorage validating")
        try:
            self.load_configuration()
            self._client = MongoClient(self._host, int(self._port))
            self._db = self._client[self._db_name]
            _threadExecutor = executor_service.new_executor("validateConnectionStorage")
            _callable = ValidateStorageConnect(self)
            _threadExecutor.submit(_callable)

        except Exception as e:
            self._log.error("MongoStorage Error {}".format(e))
            self._log.exception(e)

        self._log.info("MongoStorage validated")

    @Invalidate
    def invalidate(self, context):
        self._log.info("MongoStorage invalidating")
        try:
            if self._client is not None:
                self._client.close()
                self._client = None
                self._db = None
        except Exception as e:
            self._log.error("MongoStorage Error {}".format(e))
            self._log.exception(e)
        self._log.info("MongoStorage invalidated")
