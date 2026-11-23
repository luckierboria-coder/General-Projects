// SPDX-License-Identifier: GPL-3.0-only
// Compiler toolchain probe. --smoke only writes a disposable keyword ESM.
using System.Reflection;
using BuildKit;
using Mutagen.Bethesda;
using Mutagen.Bethesda.Starfield;

static void Usage()
{
    Console.WriteLine("BuildProbe --check-deps");
    Console.WriteLine("BuildProbe --smoke <Starfield-Data-directory> <output-directory>");
    Console.WriteLine("The smoke ESM is for serializer testing only; do not install it as a real mod.");
}

try
{
    if (args.Length == 1 && args[0] == "--check-deps")
    {
        var buildKit = typeof(GameData).Assembly.GetName();
        var mutagen = Assembly.Load("Mutagen.Bethesda.Starfield").GetName();
        Console.WriteLine($"BuildKit assembly: {buildKit.Name} {buildKit.Version}");
        Console.WriteLine($"Mutagen assembly: {mutagen.Name} {mutagen.Version}");
        Console.WriteLine("Dependency probe OK. No ESM generated or tested.");
        return;
    }

    if (args.Length == 3 && args[0] == "--smoke")
    {
        string dataDir = Path.GetFullPath(args[1]);
        string outputDir = Path.GetFullPath(args[2]);
        if (!File.Exists(Path.Combine(dataDir, "Starfield.esm")))
            throw new FileNotFoundException("A legally installed Starfield.esm is required.", Path.Combine(dataDir, "Starfield.esm"));

        Directory.CreateDirectory(outputDir);
        using var game = new GameData(dataDir);
        game.Open("Starfield.esm");

        var mod = Plugin.New(
            "STF_CompilerSmoke.esm",
            PluginStyle.Light,
            "Starfield-Transmog-Framework",
            "Serializer smoke test, not a playable transmog release");
        mod.Keywords.AddNew("STF_SmokeTest_Keyword");

        Console.WriteLine(IdLock.Apply(mod, Path.Combine(outputDir, "ids.lock.json")));
        PluginWriter.Write(mod, outputDir, game);
        Console.WriteLine("Smoke plugin written; validate with SF1Edit and sf-mod-check.");
        return;
    }

    Usage();
    Environment.ExitCode = 2;
}
catch (Exception error)
{
    Console.Error.WriteLine($"{error.GetType().Name}: {error.Message}");
    Environment.ExitCode = 1;
}
