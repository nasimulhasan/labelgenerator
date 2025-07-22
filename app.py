<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Label Generator</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
</head>
<body class="bg-light">
  <div class="container py-5">
    <h2 class="mb-4 text-center">Label Generator</h2>

    <!-- Header/Footer Upload -->
    <div class="card mb-4">
      <div class="card-body">
        <h5 class="card-title">Upload Header & Footer</h5>
        <form id="headerFooterForm" enctype="multipart/form-data">
          <div class="mb-3">
            <label for="header" class="form-label">Header PNG</label>
            <input class="form-control" type="file" name="header" accept="image/png">
          </div>
          <div class="mb-3">
            <label for="footer" class="form-label">Footer PNG</label>
            <input class="form-control" type="file" name="footer" accept="image/png">
          </div>
          <button class="btn btn-primary" type="submit">Upload Header/Footer</button>
        </form>
      </div>
    </div>

    <!-- Mode Toggle -->
    <div class="mb-4">
      <label class="form-label">Choose Input Mode:</label><br>
      <div class="form-check form-check-inline">
        <input class="form-check-input" type="radio" name="mode" id="excelMode" checked>
        <label class="form-check-label" for="excelMode">Excel Upload</label>
      </div>
      <div class="form-check form-check-inline">
        <input class="form-check-input" type="radio" name="mode" id="manualMode">
        <label class="form-check-label" for="manualMode">Manual Entry</label>
      </div>
    </div>

    <!-- Excel Mode Section -->
    <div id="excelSection">
      <div class="card">
        <div class="card-body">
          <h5 class="card-title">Upload Excel & Select Invoice Range</h5>
          <form id="excelForm" enctype="multipart/form-data">
            <div class="mb-3">
              <label class="form-label">Excel File (.xlsx)</label>
              <input class="form-control" type="file" name="excel_file" id="excelFile" accept=".xlsx,.xls">
            </div>
            <div class="mb-3">
              <label class="form-label">Start Invoice</label>
              <select class="form-select" id="startInvoice"></select>
            </div>
            <div class="mb-3">
              <label class="form-label">End Invoice</label>
              <select class="form-select" id="endInvoice"></select>
            </div>
            <button type="submit" class="btn btn-success">Generate Labels</button>
          </form>
        </div>
      </div>
    </div>

    <!-- Manual Entry Section -->
    <div id="manualSection" style="display: none;">
      <div class="card">
        <div class="card-body">
          <h5 class="card-title">Manual Label Entry</h5>
          <form id="manualForm">
            <div class="mb-2">
              <input class="form-control" name="invoice" placeholder="Invoice Number" required>
            </div>
            <div class="mb-2">
              <input class="form-control" name="name" placeholder="Customer Name" required>
            </div>
            <div class="mb-2">
              <input class="form-control" name="phone" placeholder="Phone Number" required>
            </div>
            <div class="mb-2">
              <textarea class="form-control" name="address" placeholder="Shipping Address" required></textarea>
            </div>
            <div class="mb-2">
              <input class="form-control" name="amount" placeholder="Total Amount (Tk)" required>
            </div>
            <div class="mb-2">
              <input class="form-control" name="note" placeholder="Note (optional)">
            </div>
            <div class="mb-2">
              <label>Items</label>
              <div id="itemList">
                <div class="input-group mb-2">
                  <input class="form-control item-name" placeholder="Item name">
                  <input class="form-control item-qty" type="number" placeholder="Qty">
                  <button class="btn btn-outline-secondary remove-item" type="button">×</button>
                </div>
              </div>
              <button class="btn btn-sm btn-outline-primary" id="addItem" type="button">Add Item</button>
            </div>
            <button class="btn btn-success mt-2" type="submit">Generate PDF</button>
          </form>
        </div>
      </div>
    </div>
  </div>

  <script>
    let excelPath = "";
    let headerPath = "", footerPath = "";

    $('input[name="mode"]').on('change', function () {
      if ($('#excelMode').is(':checked')) {
        $('#excelSection').show();
        $('#manualSection').hide();
      } else {
        $('#excelSection').hide();
        $('#manualSection').show();
      }
    });

    $('#headerFooterForm').submit(function (e) {
      e.preventDefault();
      const formData = new FormData(this);
      $.ajax({
        url: '/upload_header_footer',
        method: 'POST',
        data: formData,
        contentType: false,
        processData: false,
        success: function (res) {
          headerPath = res.header_path;
          footerPath = res.footer_path;
          alert('Header/Footer uploaded successfully');
        }
      });
    });

    $('#excelFile').on('change', function () {
      const formData = new FormData($('#excelForm')[0]);
      $.ajax({
        url: '/upload_excel',
        method: 'POST',
        data: formData,
        contentType: false,
        processData: false,
        success: function (res) {
          const list = res.invoices;
          excelPath = res.path;
          $('#startInvoice, #endInvoice').empty();
          list.forEach(inv => {
            $('#startInvoice, #endInvoice').append(`<option value="${inv}">${inv}</option>`);
          });
        }
      });
    });

    $('#excelForm').submit(function (e) {
      e.preventDefault();
      const start = $('#startInvoice').val();
      const end = $('#endInvoice').val();

      $.ajax({
        url: '/generate_excel_labels',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
          file_path: excelPath,
          start_invoice: start,
          end_invoice: end,
          header_file: headerPath,
          footer_file: footerPath
        }),
        xhrFields: {
          responseType: 'blob'
        },
        success: function (data) {
          const blob = new Blob([data]);
          const link = document.createElement('a');
          link.href = window.URL.createObjectURL(blob);
          link.download = 'shipping_labels_all.zip';
          link.click();
        }
      });
    });

    $(document).on('click', '#addItem', function () {
      $('#itemList').append(`
        <div class="input-group mb-2">
          <input class="form-control item-name" placeholder="Item name">
          <input class="form-control item-qty" type="number" placeholder="Qty">
          <button class="btn btn-outline-secondary remove-item" type="button">×</button>
        </div>`);
    });

    $(document).on('click', '.remove-item', function () {
      $(this).closest('.input-group').remove();
    });
  </script>
</body>
</html>
