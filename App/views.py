import os
from datetime import datetime
from django.http import JsonResponse, FileResponse, Http404
from django.db import connection
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.views.decorators.http import require_GET

# Base network path
NETWORK_PATH = r"\\192.168.4.100\jboss\jbossnow\deploy\now.ear\nowui.war\multimedia"


def mrn_form(request):
    legal_name = None
    document_url = None
    uploaded_files = []

    # ---------------- AJAX GET: MRN search + related files ----------------
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        mrn_value = request.GET.get('mrn')
        legal_name = None
        uploaded_files = []

        if mrn_value:
            # Get legal name
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT bp."LEGALNAME1"
                    FROM MRNHEADER mh
                    JOIN ORDERPARTNER op 
                        ON op."CUSTOMERSUPPLIERCODE" = mh."ORDPRNCUSTOMERSUPPLIERCODE"
                    JOIN BUSINESSPARTNER bp
                        ON bp."NUMBERID" = op."ORDERBUSINESSPARTNERNUMBERID"
                    WHERE mh."CODE" = %s
                """, [mrn_value])
                row = cursor.fetchone()
                if row:
                    legal_name = row[0]

            # Get uploaded files
            year_folder = str(datetime.now().year)
            possible_folder = os.path.join(NETWORK_PATH, "MRN", year_folder)
            for root, dirs, files in os.walk(possible_folder):
                for file in files:
                    if mrn_value in file:
                        full_path = os.path.join(root, file)
                        relative_path = full_path.replace(NETWORK_PATH, '').lstrip("\\/")
                        download_url = f"/download/?path={relative_path}"
                        uploaded_files.append({
                            "name": file,
                            "url": download_url
                        })

        return JsonResponse({'legal_name': legal_name, 'files': uploaded_files})

    # ---------------- POST: Handle file upload ----------------
    elif request.method == 'POST':
        mrn_number = request.POST.get('mrn')
        uploaded_file = request.FILES.get('document')
        custom_description = request.POST.get('description') or "document"

        company_code = division_code = legal_name = None

        if uploaded_file and mrn_number:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        mal."COMPANYCODE",
                        mal."DIVISIONCODE",
                        bp."LEGALNAME1"
                    FROM MRNHEADER mh
                    JOIN ORDERPARTNER op 
                        ON op."CUSTOMERSUPPLIERCODE" = mh."ORDPRNCUSTOMERSUPPLIERCODE"
                    JOIN BUSINESSPARTNER bp
                        ON bp."NUMBERID" = op."ORDERBUSINESSPARTNERNUMBERID"
                    JOIN MRNAUTHORIZATIONLEVEL mal
                        ON mal."MRNHEADERCODE" = mh."CODE"
                    WHERE mh."CODE" = %s                                        
                """, [mrn_number])
                row = cursor.fetchone()
                if row:
                    company_code, division_code, legal_name = row
                else:
                    company_code = 'unknown'
                    division_code = 'unknown'

            # Ensure MRN folder exists
            mrn_root_folder = os.path.join(NETWORK_PATH, "MRN")
            os.makedirs(mrn_root_folder, exist_ok=True)

            current_year = datetime.now().year
            mrn_folder = os.path.join(
                mrn_root_folder,
                str(current_year),
                str(company_code),
                str(division_code)
            )
            os.makedirs(mrn_folder, exist_ok=True)

            # Create unique filename
            base_filename = f"{custom_description}_{mrn_number}"
            extension = os.path.splitext(uploaded_file.name)[1]
            counter = 1
            final_filename = f"{base_filename}_{counter}{extension}"
            while os.path.exists(os.path.join(mrn_folder, final_filename)):
                counter += 1
                final_filename = f"{base_filename}_{counter}{extension}"

            fs = FileSystemStorage(location=mrn_folder)
            fs.save(final_filename, uploaded_file)
            document_url = os.path.join(mrn_folder, final_filename)

        # Fetch updated file list
        uploaded_files = []
        year_folder = str(datetime.now().year)
        possible_folder = os.path.join(NETWORK_PATH, "MRN", year_folder)
        for root, dirs, files in os.walk(possible_folder):
            for file in files:
                if mrn_number in file:
                    full_path = os.path.join(root, file)
                    relative_path = full_path.replace(NETWORK_PATH, '').lstrip("\\/")
                    download_url = f"/download/?path={relative_path}"
                    uploaded_files.append({
                        "name": file,
                        "url": download_url
                    })

        return render(request, 'App/mrn_form.html', {
            'legal_name': legal_name,
            'document_url': document_url,
            'uploaded_files': uploaded_files,
        })

    # ---------------- Default GET ----------------
    return render(request, 'App/mrn_form.html')


@require_GET
def download_file(request):
    file_path = request.GET.get('path')
    if not file_path:
        raise Http404("File not found.")
    safe_full_path = os.path.join(NETWORK_PATH, file_path.strip("\\/"))
    if not os.path.exists(safe_full_path):
        raise Http404("File does not exist.")
    return FileResponse(open(safe_full_path, 'rb'), as_attachment=True, filename=os.path.basename(safe_full_path))
