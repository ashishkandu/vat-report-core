from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from reporting.models import CompanyInfo  # Assuming CompanyInfo is here

if TYPE_CHECKING:
    from logging import Logger

    from .config.base import SharedSettings

logger = logging.getLogger(__name__)


def get_company_info_from_args_or_settings(
    pan: str | None,
    office_name: str | None,
    settings: SharedSettings,
    logger_instance: Logger,  # Pass logger to the util function
) -> CompanyInfo:
    """
    Constructs and returns the CompanyInfo DTO, prioritizing provided arguments over settings.

    Args:
        pan: Company PAN string, or None.
        office_name: Company office name string, or None.
        settings: SharedSettings instance.
        logger_instance: Logger instance for logging messages.

    Returns:
        A CompanyInfo object.

    Raises:
        ValueError: If Company PAN or Office Name is missing after checking all sources.

    """
    final_pan = pan if pan else settings.COMPANY_PAN
    final_office_name = office_name if office_name else settings.COMPANY_OFFICE_NAME

    if not final_pan:
        logger_instance.error(
            "Company PAN is missing. Please provide via --pan or configure in settings.",
        )
        msg = "Company PAN is required."
        raise ValueError(msg)
    if not final_office_name:
        logger_instance.error(
            "Company Office Name is missing. Please provide via --office-name or configure in settings.",
        )
        msg = "Company Office Name is required."
        raise ValueError(msg)

    company_info = CompanyInfo(pan_no=final_pan, office_name=final_office_name)
    logger_instance.info(
        "Using Company Info: PAN=%s, Office Name='%s'.",
        company_info.pan_no,
        company_info.office_name,
    )
    return company_info
