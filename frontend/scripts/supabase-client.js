// supabase-client.js
// Manages optional initialization and lazy loading of the Supabase client
(function (global) {
  var supabaseClient = null;

  function loadSupabaseScript(callback) {
    if (global.supabase) {
      callback();
      return;
    }
    var script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2";
    script.async = true;
    script.onload = function () {
      callback();
    };
    script.onerror = function () {
      console.error("Failed to load Supabase JS SDK via CDN.");
    };
    document.head.appendChild(script);
  }

  function init() {
    var url = global.SUPABASE_URL || (global.env && global.env.SUPABASE_URL);
    var key = global.SUPABASE_ANON_KEY || (global.env && global.env.SUPABASE_ANON_KEY);
    
    if (url && key) {
      loadSupabaseScript(function () {
        try {
          supabaseClient = global.supabase.createClient(url, key);
          console.log("Supabase client initialized successfully.");
        } catch (e) {
          console.error("Error creating Supabase client:", e);
        }
      });
    }
  }

  // Initialize immediately on script load if configuration is present
  init();

  // Export lazy retrieval utility
  global.getSupabaseClient = function (callback) {
    var url = global.SUPABASE_URL || (global.env && global.env.SUPABASE_URL);
    var key = global.SUPABASE_ANON_KEY || (global.env && global.env.SUPABASE_ANON_KEY);
    if (!url || !key) {
      callback(null);
      return;
    }
    if (supabaseClient) {
      callback(supabaseClient);
      return;
    }
    loadSupabaseScript(function () {
      try {
        if (!supabaseClient) {
          supabaseClient = global.supabase.createClient(url, key);
        }
        callback(supabaseClient);
      } catch (e) {
        console.error("Error lazy-creating Supabase client:", e);
        callback(null);
      }
    });
  };
})(window);
