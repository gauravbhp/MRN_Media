from django.shortcuts import render
from django.db import connection  # to run raw SQL safely

def mrn_form(request):
    legal_name = None   # default

    if request.method == 'POST':
        mrn_value = request.POST.get('mrn')  # input from form
        
        # run your SQL safely with parameter substitution
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT bp.LEGALNAME1
                FROM MRNHEADER mh
                JOIN ORDERPARTNER op 
                    ON op.CUSTOMERSUPPLIERCODE = mh.ORDPRNCUSTOMERSUPPLIERCODE
                JOIN BUSINESSPARTNER bp
                    ON bp.NUMBERID = op.ORDERBUSINESSPARTNERNUMBERID
                WHERE mh.CODE = %s
            """, [mrn_value])
            row = cursor.fetchone()
            if row:
                legal_name = row[0] 

    return render(request, 'App/mrn_form.html', {'legal_name': legal_name})
