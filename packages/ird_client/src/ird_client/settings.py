from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from shared.constants import CommonReportType


class IrdClientSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_prefix="IRD_",
    )

    # CBMS Portal Credentials
    CBMS_USERNAME: str = Field(..., description="Username for CBMS portal")
    CBMS_PASSWORD: str = Field(..., description="Password for CBMS portal")

    TAXPAYER_ID: str = Field(..., description="Taxpayer ID to use in CBMS, e.g. PAN")

    hash_value: dict = Field(
        default={
            CommonReportType.PURCHASE: "b71b8f9477168af708e7038f565f32c7",
            CommonReportType.SALES: "4b9e0405c71ff6631ab14eaf6fb19d9f",
            CommonReportType.LAKH_TRANSACTIONS: "d73ff4586f22c333a5ea17e0e4c3de95",
        },
    )

    cbms_template_endpoints: dict = Field(
        {
            CommonReportType.SALES: "/api/billingregister/BillingRegister/excelFile/1",
            CommonReportType.PURCHASE: "/api/billingregister/BillingRegister/excelFile/2",
        },
    )

    CBMS_BASE_URL: str = "https://cbms.ird.gov.np:8051"
    CBMS_LOGIN_ENDPOINT: str = "/api/auth/login"

    TAXPAYER_BASE_URL: str = "https://taxpayerportal.ird.gov.np"

    # Define the endpoint for TaxPayer templates
    taxpayer_template_endpoints: dict = {
        CommonReportType.LAKH_TRANSACTIONS: "Sample%20Files/Transaction%20Above%20One%20Lakh%20Sample%20Document.xls",
    }
