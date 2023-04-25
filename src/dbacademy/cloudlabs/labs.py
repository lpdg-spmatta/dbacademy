from typing import List, Dict, Any, Union

from dbacademy.cloudlabs import CloudlabsApi, Tenant
from dbacademy.dougrest import DatabricksApi
from dbacademy.dougrest.workspace import Workspace
from dbacademy.rest.common import ApiContainer, DatabricksApiException

Lab = Dict[str, Any]


class Labs(ApiContainer):
    def __init__(self, tenant: Tenant):
        self.tenant = tenant

    @staticmethod
    def to_id(lab: Union[int, Lab]) -> int:
        if isinstance(lab, int):
            return lab
        elif isinstance(lab, dict):
            return lab["Id"]
        else:
            raise ValueError(f"lab must be int or dict, found {type(lab)}")

    def list(self, include_expired: bool = False, include_test: bool = False) -> List[Lab]:
        state = 4 if include_expired else 1
        state += 1 if include_test else 0
        labs = self.tenant.api("POST", "/api/OnDemandLab/GetOnDemandLabs", {
            "State": str(state),
            "InstructorId": None,
            "StartIndex": 1000,  # Page size
            "PageCount": 1,
        })
        return labs

    def find_one_by_key(self, key: str, value: Union[str, int]) -> Lab:
        labs = self.list(include_expired=True, include_test=True)
        for lab in labs:
            if lab[key] == value:
                return lab
        else:
            raise DatabricksApiException(f"No lab found with {key}={value!r}", 404)

    def find_all_by_key(self, key: str, value: Union[str, int]) -> List[Lab]:
        labs = self.list(include_expired=True, include_test=True)
        return [lab for lab in labs if lab[key] == value]

    def get_by_id(self, lab_id: int) -> Lab:
        return self.find_one_by_key("Id", lab_id)

    def get_by_bitly(self, bitly_url: str) -> Lab:
        return self.find_one_by_key("BitLink", bitly_url)

    def get_by_title(self, title: str) -> Lab:
        return self.find_one_by_key("Title", title)

    def workspaces(self, lab: Union[int, Lab]) -> Workspace:
        import requests
        lab_id = Labs.to_id(lab)
        try:
            response = self.tenant.api("PUT", f"/api/Export/GetDatabricksWorkspace?eventId={lab_id}", _result_type=str)
        except requests.exceptions.HTTPError as e:
            if '"ErrorDetail":"Index was out of range.' in e.response.text:
                return []
            else:
                raise e
        import csv
        from io import StringIO
        rows = [line for line in csv.reader(StringIO(response))]
        for i, row in enumerate(rows):
            for j, col in enumerate(row):
                row[j] = col.strip()
        header = rows[0]
        workspaces = []
        for row in rows[1:]:
            assert len(row) == len(header)
            row = dict(zip(header, row))
            workspace = DatabricksApi(hostname=row["Url"][8:], token=row["Token"], deployment_name=lab["Title"])
            workspaces.append(workspace)
        return workspaces
