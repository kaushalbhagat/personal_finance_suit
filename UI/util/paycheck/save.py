from datetime import datetime
from sqlmodel import Session
from database.paycheck_models import Paycheck, PaycheckLineItem


def save_paycheck_to_db(parsed_data: dict, session: Session):
    """
    Takes the populated paycheck_data dictionary, flattens the nested items,
    and commits them to the database within a single transaction.
    """
    # Convert date string '07/02/2026' to a proper python datetime object
    date_obj = datetime.strptime(parsed_data["Pay Date"], "%m/%d/%Y")
    
    # Create the parent record
    db_paycheck = Paycheck(
        pay_date=date_obj,
        net_pay=parsed_data["Net Pay"]
    )
    session.add(db_paycheck)
    session.flush()  # Flushes to DB to generate db_paycheck.id without committing yet
    
    line_items = []
    
    # Process top-level "Income" group
    for name, amt in parsed_data["Income"].items():
        line_items.append(
            PaycheckLineItem(paycheck_id=db_paycheck.id, category="Income", name=name, amount=amt)
        )
        
    # Process nested "Deductions" groups (Taxes, Pre-Tax Benefits, Post-Tax Deductions)
    for sub_category, items_dict in parsed_data["Deductions"].items():
        for name, amt in items_dict.items():
            line_items.append(
                PaycheckLineItem(paycheck_id=db_paycheck.id, category=sub_category, name=name, amount=amt)
            )
            
    # Add all line items and commit the transaction
    session.add_all(line_items)
    session.commit()
    print(f"Successfully saved paycheck record for {parsed_data['Pay Date']} with ID: {db_paycheck.id}")


# ---- 3. Execution Example ----
# engine = create_engine("sqlite:///database.db")
# SQLModel.metadata.create_all(engine)
#
# with Session(engine) as session:
#     save_paycheck_to_db(populated_paycheck_data, session)