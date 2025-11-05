// Asset Register Export and Print Functions

// Store current asset data globally
window.currentAssetData = [];

// Function to print asset register
window.printAssetRegister = function () {
    const printWindow = window.open('', '_blank');
    const assets = window.currentAssetData || [];

    const totalPurchaseCost = assets.reduce((sum, a) => sum + (parseFloat(a.purchase_cost) || 0), 0);
    const totalCurrentValue = assets.reduce((sum, a) => sum + (parseFloat(a.current_value) || 0), 0);

    const html = `<!DOCTYPE html>
<html>
<head>
    <title>Asset Register - ${new Date().toLocaleDateString()}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { text-align: center; color: #333; margin-bottom: 5px; }
        .meta { text-align: center; color: #999; font-size: 12px; margin-bottom: 30px; }
        table { width: 100%; border-collapse: collapse; font-size: 11px; }
        th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 8px; text-align: left; font-weight: bold; }
        td { border: 1px solid #dee2e6; padding: 6px; }
        .text-end { text-align: right; }
        .total-row { font-weight: bold; background-color: #e9ecef; }
        .badge { padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; }
        .badge-active { background-color: #d1e7dd; color: #0f5132; }
        .badge-inactive { background-color: #f8d7da; color: #842029; }
        @media print {
            body { margin: 0; }
            @page { margin: 1cm; }
        }
    </style>
</head>
<body>
    <h1>Complete Asset Register</h1>
    <div class="meta">Generated on ${new Date().toLocaleString()} | Total Assets: ${assets.length}</div>

    <table>
        <thead>
            <tr>
                <th>Code</th>
                <th>Asset Name</th>
                <th>Category</th>
                <th>Status</th>
                <th>Serial/Reg</th>
                <th class="text-end">Purchase Cost</th>
                <th class="text-end">Current Value</th>
                <th class="text-end">Depreciation</th>
            </tr>
        </thead>
        <tbody>
            ${assets.map(a => {
        const purchaseCost = parseFloat(a.purchase_cost) || 0;
        const currentValue = parseFloat(a.current_value) || 0;
        const depreciation = purchaseCost - currentValue;
        const statusClass = a.status === 'ACTIVE' ? 'badge-active' : 'badge-inactive';

        return `
                    <tr>
                        <td>${a.asset_code || 'N/A'}</td>
                        <td>${a.name || 'Unknown'}</td>
                        <td>${a.category || ''}</td>
                        <td><span class="badge ${statusClass}">${a.status || 'N/A'}</span></td>
                        <td>${a.serial_number || '-'}</td>
                        <td class="text-end">${purchaseCost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td class="text-end">${currentValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td class="text-end">${depreciation.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    </tr>
                `;
    }).join('')}
        </tbody>
        <tfoot>
            <tr class="total-row">
                <td colspan="5">TOTALS</td>
                <td class="text-end">${totalPurchaseCost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td class="text-end">${totalCurrentValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td class="text-end">${(totalPurchaseCost - totalCurrentValue).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
            </tr>
        </tfoot>
    </table>
</body>
</html>`;

    printWindow.document.write(html);
    printWindow.document.close();
    setTimeout(() => {
        printWindow.print();
    }, 250);
};

// Function to export asset register as CSV
window.exportAssetRegisterCSV = function () {
    const assets = window.currentAssetData || [];

    // CSV headers
    const headers = ['Code', 'Asset Name', 'Category', 'Type', 'Status', 'Serial/Reg', 'Purchase Cost', 'Current Value', 'Depreciation'];

    // CSV rows
    const rows = assets.map(a => {
        const purchaseCost = parseFloat(a.purchase_cost) || 0;
        const currentValue = parseFloat(a.current_value) || 0;
        const depreciation = purchaseCost - currentValue;

        return [
            a.asset_code || 'N/A',
            (a.name || 'Unknown').replace(/,/g, ';'), // Replace commas to avoid CSV issues
            a.category || '',
            a.asset_type || '',
            a.status || 'N/A',
            a.serial_number || '-',
            purchaseCost.toFixed(2),
            currentValue.toFixed(2),
            depreciation.toFixed(2)
        ];
    });

    // Calculate totals
    const totalPurchaseCost = assets.reduce((sum, a) => sum + (parseFloat(a.purchase_cost) || 0), 0);
    const totalCurrentValue = assets.reduce((sum, a) => sum + (parseFloat(a.current_value) || 0), 0);

    // Add totals row
    rows.push([
        '',
        '',
        '',
        '',
        'TOTALS',
        '',
        totalPurchaseCost.toFixed(2),
        totalCurrentValue.toFixed(2),
        (totalPurchaseCost - totalCurrentValue).toFixed(2)
    ]);

    // Combine headers and rows
    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.join(','))
    ].join('\n');

    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', `asset_register_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

console.log('✅ Asset export functions loaded');
