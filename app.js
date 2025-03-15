// Hardcoded product data (simulating a database)
    const products = [
      { 
        id: 1, 
        name: "Milk (1L)", 
        brand: "Devondale",
        price: { woolworths: 3.00, coles: 3.10, aldi: 2.90 } 
      },
      { 
        id: 2, 
        name: "Bread", 
        brand: "Wonder White",
        price: { woolworths: 3.50, coles: 3.60, aldi: 3.20 } 
      },
      { 
        id: 3, 
        name: "Eggs (12)", 
        brand: "Farm Fresh",
        price: { woolworths: 6.00, coles: 6.20, aldi: 5.80 } 
      },
      { 
        id: 4, 
        name: "Apples (1kg)", 
        brand: "Pink Lady",
        price: { woolworths: 4.00, coles: 4.10, aldi: 3.80 } 
      }
    ];

    // DOM elements
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const searchResults = document.getElementById('searchResults');
    const shoppingList = document.getElementById('shoppingList');
    const addItemInput = document.getElementById('addItemInput');
    const addItemButton = document.getElementById('addItemButton');

    // Search function
    function searchProducts() {
      const searchTerm = searchInput.value.toLowerCase();
      const results = products.filter(product => 
        product.name.toLowerCase().includes(searchTerm) || 
        product.brand.toLowerCase().includes(searchTerm)
      );
      displaySearchResults(results);
    }

    // Display search results
    function displaySearchResults(results) {
      searchResults.innerHTML = '';
      if (results.length === 0) {
        searchResults.textContent = 'No products found.';
        return;
      }

      results.forEach(product => {
        const productDiv = document.createElement('div');
        productDiv.innerHTML = `
          <b>${product.name}</b> - ${product.brand}<br>
          Woolworths: $${product.price.woolworths.toFixed(2)}<br>
          Coles: $${product.price.coles.toFixed(2)}<br>
          Aldi: $${product.price.aldi.toFixed(2)}<br>
          <button onclick="addItemToShoppingList(${product.id})">Add to List</button>
        `;
        searchResults.appendChild(productDiv);
      });
    }

    // Add item to shopping list
    function addItemToShoppingList(productId) {
      const product = products.find(p => p.id === productId);
      if (!product) return;

      const listItem = document.createElement('li');
      listItem.textContent = `${product.name} - ${product.brand}`;
      shoppingList.appendChild(listItem);
    }

    // Event listeners
    searchButton.addEventListener('click', searchProducts);
    addItemButton.addEventListener('click', () => {
      const itemName = addItemInput.value.trim();
      if (itemName) {
        const listItem = document.createElement('li');
        listItem.textContent = itemName;
        shoppingList.appendChild(listItem);
        addItemInput.value = '';
      }
    });

    // Initialize the application
    document.addEventListener('DOMContentLoaded', () => {
      // Add enter key support for search
      searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          searchProducts();
        }
      });

      // Add enter key support for adding items
      addItemInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          const itemName = addItemInput.value.trim();
          if (itemName) {
            const listItem = document.createElement('li');
            listItem.textContent = itemName;
            shoppingList.appendChild(listItem);
            addItemInput.value = '';
          }
        }
      });
    });
