document.addEventListener("DOMContentLoaded", function() {
  const regionInput = document.getElementById("id_region");
  const districtInput = document.getElementById("id_district");

  function autocomplete(input, url, listId) {
      input.addEventListener("input", function() {
          let query = input.value;
          if(query.length < 1) { document.getElementById(listId).innerHTML = ""; return; }
          fetch(`${url}?q=${query}`)
              .then(response => response.json())
              .then(data => {
                  let list = document.getElementById(listId);
                  list.innerHTML = "";
                  data.forEach(item => {
                      let li = document.createElement("li");
                      li.textContent = item;
                      li.classList.add("autocomplete-item");
                      li.addEventListener("click", function() {
                          input.value = item;
                          list.innerHTML = "";
                      });
                      list.appendChild(li);
                  });
              });
      });
  }

  autocomplete(regionInput, "/autocomplete/region/", "region-list");
  autocomplete(districtInput, "/autocomplete/district/", "district-list");
});
