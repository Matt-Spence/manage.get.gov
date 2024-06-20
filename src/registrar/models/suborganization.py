from django.db import models
from .utility.time_stamped_model import TimeStampedModel
from registrar.models.portfolio import Portfolio


class Suborganization(TimeStampedModel):
    """
    TODO: Write DomainGroup description
    """
    name = models.CharField(
        null=True,
        blank=True,
        unique=True,
        help_text="Domain group",
    )

    portfolio = models.ForeignKey(
        "registrar.Portfolio",
        on_delete=models.PROTECT,
    )

    def __str__(self) -> str:
        return f"{self.name}"
