import traceback
try:
    import backend.main
    print("Import success")
except Exception as e:
    traceback.print_exc()
