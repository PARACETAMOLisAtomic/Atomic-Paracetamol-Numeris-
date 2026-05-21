import os
import sys

def setup_external_tools():
    """
    Sets up the environment files for external tools by pulling values from the main .env.
    """
    project_root = os.getcwd()
    main_env_path = os.path.join(project_root, ".env")
    
    if not os.path.exists(main_env_path):
        print("❌ Main .env file not found. Please create it first.")
        return

    # Read main .env
    env_values = {}
    with open(main_env_path, "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                env_values[key] = val

    # --- Setup MiroFish ---
    mirofish_dir = os.path.join(project_root, "backend", "external", "mirofish")
    if os.path.exists(mirofish_dir):
        print("🔧 Setting up MiroFish environment...")
        miro_env_path = os.path.join(mirofish_dir, ".env")
        miro_content = [
            f"LLM_API_KEY={env_values.get('MIROFISH_LLM_API_KEY', '')}",
            f"LLM_BASE_URL={env_values.get('MIROFISH_LLM_BASE_URL', 'https://api.openai.com/v1')}",
            f"LLM_MODEL_NAME={env_values.get('MIROFISH_LLM_MODEL_NAME', 'gpt-4o')}",
            f"ZEP_API_KEY={env_values.get('MIROFISH_ZEP_API_KEY', '')}"
        ]
        with open(miro_env_path, "w") as f:
            f.write("\n".join(miro_content))
        print("✅ MiroFish .env created.")

    # --- Setup WorldMonitor ---
    wm_dir = os.path.join(project_root, "backend", "external", "worldmonitor")
    if os.path.exists(wm_dir):
        print("🔧 Setting up WorldMonitor environment...")
        wm_env_path = os.path.join(wm_dir, ".env.local")
        wm_content = [
            f"GROQ_API_KEY={env_values.get('WORLDMONITOR_GROQ_API_KEY', '')}",
            f"FINNHUB_API_KEY={env_values.get('WORLDMONITOR_FINNHUB_API_KEY', '')}",
            f"FRED_API_KEY={env_values.get('WORLDMONITOR_FRED_API_KEY', '')}",
            f"EIA_API_KEY={env_values.get('WORLDMONITOR_EIA_API_KEY', '')}"
        ]
        with open(wm_env_path, "w") as f:
            f.write("\n".join(wm_content))
        print("✅ WorldMonitor .env.local created.")

    # --- Setup Kite MCP ---
    kite_mcp_dir = os.path.join(project_root, "backend", "external", "kite-mcp-server")
    if os.path.exists(kite_mcp_dir):
        print("🔧 Setting up Kite MCP Server environment...")
        kite_env_path = os.path.join(kite_mcp_dir, ".env")
        kite_content = [
            f"KITE_API_KEY={env_values.get('ZERODHA_API_KEY', '')}",
            f"KITE_API_SECRET={env_values.get('ZERODHA_API_SECRET', '')}",
            "APP_MODE=http",
            "APP_PORT=8081", # Use 8081 to avoid conflict with main backend if it uses 8080
            "APP_HOST=localhost",
            "LOG_LEVEL=info"
        ]
        with open(kite_env_path, "w") as f:
            f.write("\n".join(kite_content))
        print("✅ Kite MCP .env created.")

    print("\n🚀 External tools setup complete! Don't forget to fill in the keys in the main .env file.")

if __name__ == "__main__":
    setup_external_tools()
