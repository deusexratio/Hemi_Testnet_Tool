from datetime import datetime

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Wallet(Base):
    __tablename__ = 'wallets'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    address: Mapped[str]
    next_action_time: Mapped[datetime | None] = mapped_column(default=None)
    today_activity_eth: Mapped[int] = mapped_column(default=0)
    today_activity_erc20: Mapped[bool] = mapped_column(default=False, server_default='0')
    today_activity_swaps: Mapped[bool] = mapped_column(default=False, server_default='0')
    insufficient_balance: Mapped[bool] = mapped_column(default=False, server_default='0')
    # twice_weekly_capsule: Mapped[int | None] = mapped_column(default=None)
    private_key: Mapped[str] = mapped_column(unique=True, index=True)
    proxy: Mapped[str]

    # bridges_eth_to_hemi: Mapped[int | None] = mapped_column(default=None)
    # bridges_eth_from_hemi: Mapped[int | None] = mapped_column(default=None)


    # okx_address: Mapped[str]
    # number_of_swaps: Mapped[int]
    # number_of_dmail: Mapped[int]
    # number_of_liquidity_stake: Mapped[int]
    # next_initial_action_time: Mapped[datetime | None] = mapped_column(default=None)
    # next_activity_action_time: Mapped[datetime | None] = mapped_column(default=None)
    # initial_completed: Mapped[bool] = mapped_column(default=False, server_default='0')
    # completed: Mapped[bool] = mapped_column(default=False, server_default='0')

    def __repr__(self):
        return f'{self.name}: {self.address}'
