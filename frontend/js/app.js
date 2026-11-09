/* TrekManage Vue 3 SPA (CDN) */
const { createApp, ref, reactive, computed, watch, nextTick, onMounted } = Vue;

const TOKEN_KEY = "trekmanage_token";
const USER_KEY = "trekmanage_user";

createApp({
  setup() {
    const token = ref(localStorage.getItem(TOKEN_KEY) || "");
    const user = ref(JSON.parse(localStorage.getItem(USER_KEY) || "null"));
    const route = ref(window.location.hash.slice(1) || "/");
    const loading = ref(false);
    const toast = reactive({ show: false, message: "", type: "success" });

    const authForm = reactive({ name: "", email: "", password: "", phone: "" });
    const adminDash = ref({});
    const adminTreks = ref([]);
    const adminStaff = ref([]);
    const adminUsers = ref([]);
    const adminBookings = ref([]);
    const notifications = ref([]);
    const searchForm = reactive({ q: "", type: "all" });
    const searchResult = ref(null);
    const reportData = ref(null);
    let chartPopular = null;
    let chartParticipants = null;

    const staffDash = ref({});
    const participantsView = ref({});
    const staffTrekForm = reactive({
      id: null,
      name: "",
      available_slots: 0,
      status: "Open",
      instructions: "",
    });

    const userDash = ref({});
    const filteredTreks = ref([]);
    const userBookings = ref([]);
    const exportJobs = ref([]);
    const filter = reactive({ q: "", difficulty: "", location: "", duration: "" });
    const profileForm = reactive({
      name: "",
      phone: "",
      address: "",
      emergency_contact: "",
      password: "",
    });

    const trekForm = reactive({
      id: null,
      name: "",
      location: "",
      difficulty: "Easy",
      duration_days: 2,
      total_slots: 10,
      available_slots: 10,
      status: "Pending",
      start_date: "",
      end_date: "",
      price: 0,
      description: "",
      instructions: "",
    });
    const assignForm = reactive({ trekId: null, trekName: "", staff_ids: [] });
    const staffForm = reactive({ name: "", email: "", phone: "", password: "Staff@123" });

    const isAdmin = computed(() => user.value?.role === "admin");
    const isStaff = computed(() => user.value?.role === "staff");
    const isUser = computed(() => user.value?.role === "user");
    const roleLabel = computed(() => {
      const map = { admin: "Admin", staff: "Trek Staff", user: "Trekker" };
      return map[user.value?.role] || "";
    });

    const navItems = computed(() => {
      if (!user.value) return [];
      if (user.value.role === "admin") {
        return [
          { to: "/admin", label: "Dashboard" },
          { to: "/admin/treks", label: "Treks" },
          { to: "/admin/staff", label: "Staff" },
          { to: "/admin/users", label: "Users" },
          { to: "/admin/bookings", label: "Bookings" },
          { to: "/admin/search", label: "Search" },
          { to: "/admin/reports", label: "Reports" },
        ];
      }
      if (user.value.role === "staff") {
        return [{ to: "/staff", label: "My treks" }];
      }
      return [
        { to: "/user", label: "Browse" },
        { to: "/user/bookings", label: "My bookings" },
        { to: "/user/profile", label: "Profile" },
      ];
    });

    const adminStatTiles = computed(() => [
      { label: "Treks", value: adminDash.value.total_treks ?? "—" },
      { label: "Users", value: adminDash.value.total_users ?? "—" },
      { label: "Staff", value: adminDash.value.total_staff ?? "—" },
      { label: "Bookings", value: adminDash.value.total_bookings ?? "—" },
    ]);

    function showToast(message, type = "success") {
      toast.message = message;
      toast.type = type;
      toast.show = true;
      setTimeout(() => (toast.show = false), 4200);
    }

    function apiUrl(path) {
      if (!path) return "#";
      return path.startsWith("http") ? path : path;
    }

    async function api(path, options = {}) {
      const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
      if (token.value) headers.Authorization = `Bearer ${token.value}`;
      const res = await fetch(path, { ...options, headers });
      let data = null;
      const text = await res.text();
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = { error: text || "Unexpected response" };
      }
      if (!res.ok) {
        const msg = data?.error || data?.message || `Request failed (${res.status})`;
        throw new Error(msg);
      }
      return data;
    }

    function homeForRole(role) {
      if (role === "admin") return "/admin";
      if (role === "staff") return "/staff";
      return "/user";
    }

    function navigate(path) {
      window.location.hash = path;
    }

    function persistAuth(accessToken, userObj) {
      token.value = accessToken;
      user.value = userObj;
      localStorage.setItem(TOKEN_KEY, accessToken);
      localStorage.setItem(USER_KEY, JSON.stringify(userObj));
    }

    function logout() {
      token.value = "";
      user.value = null;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      navigate("/login");
    }

    function formatDate(value) {
      if (!value) return "—";
      return String(value).slice(0, 10);
    }

    async function doLogin() {
      if (!authForm.email || !authForm.password) {
        showToast("Email and password required", "danger");
        return;
      }
      loading.value = true;
      try {
        const data = await api("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ email: authForm.email, password: authForm.password }),
        });
        persistAuth(data.access_token, data.user);
        showToast(`Welcome, ${data.user.name}`);
        navigate(homeForRole(data.user.role));
      } catch (e) {
        showToast(e.message, "danger");
      } finally {
        loading.value = false;
      }
    }

    async function doRegister() {
      if (!authForm.name || authForm.name.length < 2) {
        showToast("Name is required", "danger");
        return;
      }
      if (!authForm.email || authForm.password.length < 6) {
        showToast("Valid email and password (min 6) required", "danger");
        return;
      }
      loading.value = true;
      try {
        const data = await api("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({ ...authForm }),
        });
        persistAuth(data.access_token, data.user);
        showToast("Account created");
        navigate("/user");
      } catch (e) {
        showToast(e.message, "danger");
      } finally {
        loading.value = false;
      }
    }

    async function loadAdminDashboard() {
      adminDash.value = await api("/api/admin/dashboard");
    }
    async function loadAdminTreks() {
      const data = await api("/api/admin/treks");
      adminTreks.value = data.treks;
      const staff = await api("/api/admin/staff");
      adminStaff.value = staff.staff;
    }
    async function loadAdminStaff() {
      const data = await api("/api/admin/staff");
      adminStaff.value = data.staff;
    }
    async function loadAdminUsers() {
      const data = await api("/api/admin/users");
      adminUsers.value = data.users;
    }
    async function loadAdminBookings() {
      const data = await api("/api/admin/bookings");
      adminBookings.value = data.bookings;
    }
    async function loadReports() {
      reportData.value = await api("/api/admin/reports/summary");
      const n = await api("/api/admin/notifications");
      notifications.value = n.notifications;
      await nextTick();
      renderCharts();
    }

    function renderCharts() {
      if (!reportData.value || typeof Chart === "undefined") return;
      const pop = reportData.value.popular_treks || [];
      const part = reportData.value.top_participants || [];
      const popCanvas = document.getElementById("chartPopular");
      const partCanvas = document.getElementById("chartParticipants");
      if (chartPopular) chartPopular.destroy();
      if (chartParticipants) chartParticipants.destroy();
      if (popCanvas) {
        chartPopular = new Chart(popCanvas, {
          type: "bar",
          data: {
            labels: pop.map((p) => p.name),
            datasets: [
              {
                label: "Bookings",
                data: pop.map((p) => p.count),
                backgroundColor: "#1f6b4a",
                borderRadius: 6,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
          },
        });
      }
      if (partCanvas) {
        chartParticipants = new Chart(partCanvas, {
          type: "doughnut",
          data: {
            labels: part.map((p) => p.name),
            datasets: [
              {
                data: part.map((p) => p.count),
                backgroundColor: ["#1f6b4a", "#3d8b6e", "#c9852c", "#2f6f9f", "#5d7268", "#8a6d3b"],
              },
            ],
          },
          options: { responsive: true, maintainAspectRatio: false },
        });
      }
    }

    async function runSearch() {
      if (!searchForm.q.trim()) {
        showToast("Enter a search query", "warning");
        return;
      }
      const q = encodeURIComponent(searchForm.q.trim());
      searchResult.value = await api(`/api/admin/search?q=${q}&type=${searchForm.type}`);
    }

    async function runMonthlyReport() {
      loading.value = true;
      try {
        const data = await api("/api/admin/reports/monthly/run", { method: "POST" });
        showToast(`Monthly report queued (task ${data.task_id})`);
        setTimeout(loadReports, 1500);
      } catch (e) {
        showToast(e.message, "danger");
      } finally {
        loading.value = false;
      }
    }

    function openTrekModal(trek = null) {
      if (trek) {
        Object.assign(trekForm, {
          id: trek.id,
          name: trek.name,
          location: trek.location,
          difficulty: trek.difficulty,
          duration_days: trek.duration_days,
          total_slots: trek.total_slots,
          available_slots: trek.available_slots,
          status: trek.status,
          start_date: trek.start_date,
          end_date: trek.end_date,
          price: trek.price,
          description: trek.description || "",
          instructions: trek.instructions || "",
        });
      } else {
        Object.assign(trekForm, {
          id: null,
          name: "",
          location: "",
          difficulty: "Easy",
          duration_days: 2,
          total_slots: 10,
          available_slots: 10,
          status: "Pending",
          start_date: "",
          end_date: "",
          price: 0,
          description: "",
          instructions: "",
        });
      }
      bootstrap.Modal.getOrCreateInstance(document.getElementById("trekModal")).show();
    }

    async function saveTrek() {
      try {
        const payload = { ...trekForm };
        delete payload.id;
        if (trekForm.id) {
          await api(`/api/admin/treks/${trekForm.id}`, {
            method: "PUT",
            body: JSON.stringify(payload),
          });
          showToast("Trek updated");
        } else {
          await api("/api/admin/treks", { method: "POST", body: JSON.stringify(payload) });
          showToast("Trek created");
        }
        bootstrap.Modal.getInstance(document.getElementById("trekModal"))?.hide();
        await loadAdminTreks();
      } catch (e) {
        showToast(e.message, "danger");
      }
    }

    async function deleteTrek(trek) {
      if (!confirm(`Delete trek "${trek.name}"?`)) return;
      try {
        await api(`/api/admin/treks/${trek.id}`, { method: "DELETE" });
        showToast("Trek deleted");
        await loadAdminTreks();
      } catch (e) {
        showToast(e.message, "danger");
      }
    }

    async function openAssignModal(trek) {
      if (!adminStaff.value.length) await loadAdminStaff();
      assignForm.trekId = trek.id;
      assignForm.trekName = trek.name;
      assignForm.staff_ids = [...(trek.assigned_staff_ids || [])];
      bootstrap.Modal.getOrCreateInstance(document.getElementById("assignModal")).show();
    }

    async function saveAssign() {
      try {
        await api(`/api/admin/treks/${assignForm.trekId}/assign-staff`, {
          method: "POST",
          body: JSON.stringify({ staff_ids: assignForm.staff_ids, replace: true }),
        });
        showToast("Staff assigned");
        bootstrap.Modal.getInstance(document.getElementById("assignModal"))?.hide();
        await loadAdminTreks();
      } catch (e) {
        showToast(e.message, "danger");
      }
    }

    function openStaffModal() {
      Object.assign(staffForm, { name: "", email: "", phone: "", password: "Staff@123" });
      bootstrap.Modal.getOrCreateInstance(document.getElementById("staffModal")).show();
    }

    async function saveStaff() {
      try {
        await api("/api/admin/staff", { method: "POST", body: JSON.stringify({ ...staffForm }) });
        showToast("Staff created");
        bootstrap.Modal.getInstance(document.getElementById("staffModal"))?.hide();
        await loadAdminStaff();
      } catch (e) {
        showToast(e.message, "danger");
      }
    }

    async function togglePerson(person, action) {
      const body =
        action === "blacklist"
          ? { is_blacklisted: true, is_active: false }
          : action === "deactivate"
            ? { is_active: false }
            : { is_active: true, is_blacklisted: false };
      try {
        await api(`/api/admin/people/${person.id}/status`, {
          method: "PATCH",
          body: JSON.stringify(body),
        });
        showToast("Status updated");
        if (person.role === "staff") await loadAdminStaff();
        else await loadAdminUsers();
      } catch (e) {
        showToast(e.message, "danger");
      }
    }

    async function loadStaffDashboard() {
      staffDash.value = await api("/api/staff/dashboard");
    }

    function openStaffTrekModal(trek) {
      Object.assign(staffTrekForm, {
        id: trek.id,
        name: trek.name,
        available_slots: trek.available_slots,
        status: ["Open", "Closed", "Completed"].includes(trek.status) ? trek.status : "Open",
        instructions: trek.instructions || "",
      });
      bootstrap.Modal.getOrCreateInstance(document.getElementById("staffTrekModal")).show();
    }

    async function saveStaffTrek() {
      try {
        await api(`/api/staff/treks/${staffTrekForm.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            available_slots: staffTrekForm.available_slots,
            status: staffTrekForm.status,
            instructions: staffTrekForm.instructions,
          }),
        });
        showToast("Trek updated");
        bootstrap.Modal.getInstance(document.getElementById("staffTrekModal"))?.hide();
        await loadStaffDashboard();
      } catch (e) {
        showToast(e.message, "danger");
      }
    }

    async function viewParticipants(trek) {
      participantsView.value = await api(`/api/staff/treks/${trek.id}/participants`);
      navigate(`/staff/trek/${trek.id}`);
    }

    async function staffMark(trek, kind) {
      try {
        const path =
          kind === "started"
            ? `/api/staff/treks/${trek.id}/mark-started`
            : `/api/staff/treks/${trek.id}/mark-completed`;
        await api(path, { method: "POST" });
        showToast(kind === "started" ? "Trek started (Closed)" : "Trek completed");
        await loadStaffDashboard();
      } catch (e) {
        showToast(e.message, "danger");
      }
    }

    async function loadUserDashboard() {
      userDash.value = await api("/api/user/dashboard");
      await filterTreks();
    }

    async function filterTreks() {
      const params = new URLSearchParams({ view: "public" });
      if (filter.q) params.set("q", filter.q);
      if (filter.difficulty) params.set("difficulty", filter.difficulty);
      if (filter.location) params.set("location", filter.location);
      if (filter.duration) params.set("duration", filter.duration);
      const data = await api(`/api/treks?${params.toString()}`);
      filteredTreks.value = data.treks;
      if (data.cached) {
        /* cached open treks via Redis */
      }
    }

    function resetFilter() {
      Object.assign(filter, { q: "", difficulty: "", location: "", duration: "" });
      filterTreks();
    }

    async function bookTrek(trek) {
      if (!confirm(`Book "${trek.name}"?`)) return;
      try {
        await api("/api/user/bookings", {
          method: "POST",
          body: JSON.stringify({ trek_id: trek.id, payment_status: "Pending" }),
        });
        showToast("Booking confirmed — notification sent");
        await loadUserDashboard();
      } catch (e) {
        showToast(e.message, "danger");
      }
    }

    async function loadUserBookings() {
      const data = await api("/api/user/bookings");
      userBookings.value = data.bookings;
      await refreshExports();
    }

    async function cancelBooking(booking) {
      if (!confirm("Cancel this booking?")) return;
      try {
        await api(`/api/user/bookings/${booking.id}/cancel`, { method: "POST" });
        showToast("Booking cancelled");
        await loadUserBookings();
      } catch (e) {
        showToast(e.message, "danger");
      }
    }

    async function exportBookings() {
      loading.value = true;
      try {
        const data = await api("/api/user/exports/bookings", { method: "POST" });
        showToast("CSV export started — you will get an alert when ready");
        exportJobs.value = [data.job, ...exportJobs.value];
        pollExport(data.job.id);
      } catch (e) {
        showToast(e.message, "danger");
      } finally {
        loading.value = false;
      }
    }

    async function refreshExports() {
      const data = await api("/api/user/exports");
      exportJobs.value = data.jobs;
    }

    function pollExport(jobId) {
      let tries = 0;
      const timer = setInterval(async () => {
        tries += 1;
        try {
          const data = await api(`/api/user/exports/${jobId}`);
          const job = data.job;
          exportJobs.value = exportJobs.value.map((j) => (j.id === jobId ? job : j));
          if (job.status === "Completed") {
            clearInterval(timer);
            showToast("Export ready — download from Exports table");
          } else if (job.status === "Failed" || tries > 40) {
            clearInterval(timer);
            if (job.status === "Failed") showToast(job.message || "Export failed", "danger");
          }
        } catch {
          clearInterval(timer);
        }
      }, 1500);
    }

    async function downloadExport(job) {
      const res = await fetch(job.download_url, {
        headers: { Authorization: `Bearer ${token.value}` },
      });
      if (!res.ok) {
        showToast("Download failed", "danger");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `bookings_${job.id}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }

    async function loadProfile() {
      const data = await api("/api/user/profile");
      Object.assign(profileForm, {
        name: data.user.name || "",
        phone: data.user.phone || "",
        address: data.user.address || "",
        emergency_contact: data.user.emergency_contact || "",
        password: "",
      });
    }

    async function saveProfile() {
      try {
        const payload = { ...profileForm };
        if (!payload.password) delete payload.password;
        const data = await api("/api/user/profile", {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        user.value = data.user;
        localStorage.setItem(USER_KEY, JSON.stringify(data.user));
        showToast("Profile saved");
      } catch (e) {
        showToast(e.message, "danger");
      }
    }

    async function loadRouteData() {
      if (!user.value) {
        if (route.value !== "/login" && route.value !== "/register") navigate("/login");
        return;
      }
      if (route.value === "/" || route.value === "") {
        navigate(homeForRole(user.value.role));
        return;
      }
      try {
        if (route.value === "/admin") await loadAdminDashboard();
        else if (route.value === "/admin/treks") await loadAdminTreks();
        else if (route.value === "/admin/staff") await loadAdminStaff();
        else if (route.value === "/admin/users") await loadAdminUsers();
        else if (route.value === "/admin/bookings") await loadAdminBookings();
        else if (route.value === "/admin/reports") await loadReports();
        else if (route.value === "/staff") await loadStaffDashboard();
        else if (route.value.startsWith("/staff/trek/")) {
          const id = route.value.split("/").pop();
          participantsView.value = await api(`/api/staff/treks/${id}/participants`);
        } else if (route.value === "/user" || route.value === "/user/browse") await loadUserDashboard();
        else if (route.value === "/user/bookings") await loadUserBookings();
        else if (route.value === "/user/profile") await loadProfile();
      } catch (e) {
        if (String(e.message).toLowerCase().includes("token") || String(e.message).includes("401")) {
          logout();
        } else {
          showToast(e.message, "danger");
        }
      }
    }

    function onHashChange() {
      route.value = window.location.hash.slice(1) || "/";
      loadRouteData();
    }

    onMounted(async () => {
      if (!window.location.hash) {
        window.location.hash = user.value ? homeForRole(user.value.role) : "/login";
      }
      window.addEventListener("hashchange", onHashChange);
      if (token.value) {
        try {
          const me = await api("/api/auth/me");
          user.value = me.user;
          localStorage.setItem(USER_KEY, JSON.stringify(me.user));
        } catch {
          logout();
          return;
        }
      }
      onHashChange();
    });

    return {
      user,
      route,
      loading,
      toast,
      authForm,
      adminDash,
      adminTreks,
      adminStaff,
      adminUsers,
      adminBookings,
      notifications,
      searchForm,
      searchResult,
      staffDash,
      participantsView,
      staffTrekForm,
      userDash,
      filteredTreks,
      userBookings,
      exportJobs,
      filter,
      profileForm,
      trekForm,
      assignForm,
      staffForm,
      isAdmin,
      isStaff,
      isUser,
      roleLabel,
      navItems,
      adminStatTiles,
      navigate,
      logout,
      formatDate,
      doLogin,
      doRegister,
      runSearch,
      runMonthlyReport,
      openTrekModal,
      saveTrek,
      deleteTrek,
      openAssignModal,
      saveAssign,
      openStaffModal,
      saveStaff,
      togglePerson,
      openStaffTrekModal,
      saveStaffTrek,
      viewParticipants,
      staffMark,
      filterTreks,
      resetFilter,
      bookTrek,
      cancelBooking,
      exportBookings,
      refreshExports,
      downloadExport,
      saveProfile,
      apiUrl,
    };
  },
}).mount("#app");
