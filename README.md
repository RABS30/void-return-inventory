# Void and Return Transaction Recorder

A web application for recording and managing retail void and return transactions. Users can identify products by barcode, attach supporting photos, review transaction history, monitor activity through a dashboard, and export reports in Excel format.

## Features

### 1. Record Void Transactions
- Record void transactions with product and cashier information.
- Select the outlet, cashier, and authorized person.
- Enter the void reason when applicable.
- Attach a supporting photo.

### 2. Record Return Transactions
- Record product return transactions.
- Enter the transaction number when available.
- Enter the selling price manually.
- Select the outlet, cashier, and authorized person.
- Enter the return reason when applicable.
- Attach a supporting photo.

### 3. Find Products by Barcode
- Search for products using their barcode.
- Retrieve product information from the product master.
- Validate barcodes against registered products.

### 4. Scan Barcodes with a Camera
- Scan product barcodes using a device camera.
- Use the scanned barcode to identify the product.

### 5. Attach Transaction Photos
- Upload supporting photos for void and return transactions.
- Enforce the maximum image size of 5 MB.

### 6. Browse and Search Transactions
- View recorded void and return transactions.
- Search and filter transaction records.
- Review transaction details.
- Delete existing transaction records.

### 7. View Dashboard Summaries
- View transaction summaries on the dashboard.
- Monitor void and return activity.

### 8. Export Excel Reports
- Export void transaction reports in Excel format (`.xlsx`).
- Export return transaction reports in Excel format (`.xlsx`).

The VOID report includes:
- Sequential report number
- Outlet
- Date
- Product name
- Barcode
- Quantity
- Cashier
- Authorized person
- Void reason

The RETURN report includes:
- Date
- Outlet
- Cashier
- Transaction number
- Product name
- Barcode
- Quantity
- Selling price
- Authorized person
- Return reason

The selling price in the RETURN report is stored as a numeric value for spreadsheet calculations.

### 9. Load the Product Master
- Load product data from the product master file.
- Validate product data before importing.
- Prevent importing product data when transaction records already exist, if enforced by the current implementation.

## Transaction Rules

- Transactions are classified as VOID or RETURN.
- Supported outlets.
- Product barcodes must match products in the product master.
- Transaction quantities must be at least 1.
- Supporting images are required and must not exceed 5 MB.
- VOID transactions do not use a transaction number or selling price.
- RETURN transactions require a manually entered selling price.
- RETURN transaction numbers are optional.
- Void and return reasons can be left empty when permitted by the form.