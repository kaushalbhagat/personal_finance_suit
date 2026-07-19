from datetime import date
from decimal import Decimal
from sqlmodel import Session, select
from database.models import Transaction, CurrentPosition, SnapshotHolding, TransactionType

def execute_stock_split(session: Session, ticker: str, split_ratio: float, split_date: date):
    """
    Executes a stock split across all database tables in a single transaction.
    Example: Apple 2-for-1 split -> split_ratio = 2.0
    """
    ratio_dec = Decimal(str(split_ratio))
    
    # 1. UPDATE CURRENT POSITION (Live Inventory)
    pos_stmt = select(CurrentPosition).where(CurrentPosition.ticker == ticker)
    position = session.scalars(pos_stmt).first()
    
    if position:
        # Quantity increases, total cost basis stays exactly the same
        position.quantity = Decimal(str(float(position.quantity) * split_ratio))
        session.add(position)

    # 2. LOG THE SPLIT TRANSACTION (Audit Trail)
    # We record this to preserve historical context for why share counts changed
    split_tx = Transaction(
        ticker=ticker,
        transaction_type=TransactionType.SPLIT,
        transaction_date=split_date,
        quantity=Decimal("0.00"),  # Or store the multiplier context here
        price_per_share=Decimal("0.00"),
        total_amount=Decimal("0.00"),
        notes=f"Stock split adjustment. Ratio: {split_ratio}:1"
    )
    session.add(split_tx)

    # 3. RETROACTIVELY ADJUST SNAPSHOT HOLDINGS
    # Updates historical quantities so back-testing and share charts stay uniform
    snap_stmt = select(SnapshotHolding).where(
        SnapshotHolding.ticker == ticker,
        SnapshotHolding.snapshot_date < split_date
    )
    historical_snapshots = session.scalars(snap_stmt).all()
    
    for snap in historical_snapshots:
        # Scale up the historical share count
        snap.quantity = Decimal(str(float(snap.quantity) * split_ratio))
        # Per-share price drops, but total value remains identical
        session.add(snap)
        
    # Flush or commit changes up to the parent Streamlit session context
    session.commit()