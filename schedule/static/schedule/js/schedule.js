(() => {
  const cityInput = document.getElementById("schedule-city");
  const latitudeInput = document.getElementById("schedule-latitude");
  const longitudeInput = document.getElementById("schedule-longitude");
  const locationButton = document.getElementById("use-current-location");
  const locationStatus = document.getElementById("location-status");
  const scheduleForm = cityInput?.form;

  if (!cityInput || !latitudeInput || !longitudeInput || !locationButton || !locationStatus || !scheduleForm) {
    return;
  }

  const hasSavedCoordinates = Boolean(latitudeInput.value && longitudeInput.value);
  cityInput.required = !hasSavedCoordinates;

  if (hasSavedCoordinates) {
    locationStatus.textContent = "Memakai lokasi perangkat yang tersimpan di sesi ini.";
  }

  const bulkForm = document.querySelector(".schedule-bulk-form");
  const selectAll = document.getElementById("select-visible-schedules");
  const scheduleCheckboxes = bulkForm?.querySelectorAll('input[name="schedule_ids"]') || [];
  if (selectAll && bulkForm) {
    const selectionCount = document.getElementById("selection-count");
    const bulkActionButtons = bulkForm.querySelectorAll(".schedule-bulk-actions button");
    const updateSelection = () => {
      const selectedCount = Array.from(scheduleCheckboxes).filter((checkbox) => checkbox.checked).length;
      if (selectionCount) {
        selectionCount.textContent = `${selectedCount} dipilih`;
      }
      selectAll.checked = scheduleCheckboxes.length > 0 && selectedCount === scheduleCheckboxes.length;
      selectAll.indeterminate = selectedCount > 0 && selectedCount < scheduleCheckboxes.length;
      bulkActionButtons.forEach((button) => {
        button.disabled = selectedCount === 0;
      });
    };

    selectAll.addEventListener("change", () => {
      scheduleCheckboxes.forEach((checkbox) => {
        checkbox.checked = selectAll.checked;
      });
      updateSelection();
    });
    scheduleCheckboxes.forEach((checkbox) => {
      checkbox.addEventListener("change", updateSelection);
    });
    updateSelection();
  }

  locationButton.addEventListener("click", () => {
    if (!navigator.geolocation) {
      locationStatus.textContent = "Browser ini belum mendukung lokasi perangkat. Masukkan kota secara manual.";
      return;
    }

    locationButton.disabled = true;
    locationStatus.textContent = "Meminta izin dan membaca lokasi perangkat...";

    navigator.geolocation.getCurrentPosition(
      (position) => {
        latitudeInput.value = position.coords.latitude.toFixed(3);
        longitudeInput.value = position.coords.longitude.toFixed(3);
        cityInput.value = "Lokasi saya";
        cityInput.required = false;
        locationButton.disabled = false;
        locationStatus.textContent = "Lokasi dipilih. Sinkronkan jadwal untuk memuat prakiraan di sekitar perangkat.";
      },
      (error) => {
        latitudeInput.value = "";
        longitudeInput.value = "";
        cityInput.required = true;
        locationButton.disabled = false;

        if (error.code === error.PERMISSION_DENIED) {
          locationStatus.textContent = "Izin lokasi ditolak. Masukkan kota secara manual atau izinkan lokasi di pengaturan browser.";
        } else if (error.code === error.TIMEOUT) {
          locationStatus.textContent = "Lokasi perangkat terlalu lama ditemukan. Coba lagi atau masukkan kota secara manual.";
        } else {
          locationStatus.textContent = "Lokasi perangkat tidak tersedia. Masukkan kota secara manual.";
        }
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 },
    );
  });

  cityInput.addEventListener("input", () => {
    if (latitudeInput.value || longitudeInput.value) {
      latitudeInput.value = "";
      longitudeInput.value = "";
      cityInput.required = true;
      locationStatus.textContent = "Memakai kota yang dimasukkan secara manual.";
    }
  });
})();
