# -*- coding: utf-8 -*-

{
    'name': 'EASY - HR Loan Tracker',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 95,
    'summary': 'Loans Validation, Reimbursing',
    'description': """
Manage loans by Employees
============================

This application allows you to manage your employees' loans. It gives you access to your employees’ fee notes and give you the right to complete and validate or refuse the notes. After validation it creates a cash ticket for the employee.
Employee can encode their own loans and the validation flow puts it automatically in the cash after validation by managers.


The whole flow is implemented as:
---------------------------------
* Draft loan
* Submitted by the employee to his manager
* Approved by his manager
* Validation by the accountant and cash entries creation
""",
    'website': 'https://www.easysol.com',
    'depends': ['hr_payroll'],
    'data': [
        'security/hr_easy_loan_security.xml',
        'security/ir.model.access.csv',
        'data/hr_easy_loan_data.xml',
        'views/hr_easy_loan_views.xml',

    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
}
