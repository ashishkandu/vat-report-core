from pydantic import BaseModel


class CompanyInfo(BaseModel):
    pan_no: str
    office_name: str


class ReportHeaderDetails(CompanyInfo):
    year: int
    month_name: str
