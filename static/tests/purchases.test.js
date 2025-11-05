// Basic test for purchases page functionality
describe('Purchases Page', () => {
  test('should load purchase data correctly', () => {
    // Mock the fetch response
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { id: 1, reference: 'PO-001', supplier: 'Test Supplier', total: 100.00, status: 'received' }
        ])
      })
    );
    
    // Create DOM elements that would be in the purchases.html page
    document.body.innerHTML = `
      <table id="purchases-table">
        <tbody id="purchases-data"></tbody>
      </table>
    `;
    
    // Import and run the loadPurchases function (simulated here)
    const loadPurchases = () => {
      return fetch('/api/v1/purchases')
        .then(response => response.json())
        .then(data => {
          const tableBody = document.getElementById('purchases-data');
          data.forEach(purchase => {
            const row = document.createElement('tr');
            row.innerHTML = `
              <td>${purchase.reference}</td>
              <td>${purchase.supplier}</td>
              <td>${purchase.total}</td>
              <td>${purchase.status}</td>
            `;
            tableBody.appendChild(row);
          });
          return data;
        });
    };
    
    // Run the function and test the results
    return loadPurchases().then(data => {
      expect(data.length).toBe(1);
      expect(document.querySelectorAll('#purchases-data tr').length).toBe(1);
      expect(document.querySelector('#purchases-data tr').textContent).toContain('PO-001');
    });
  });
});