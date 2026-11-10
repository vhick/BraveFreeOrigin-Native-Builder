// Brave Free Origin Native Host, b1r1. MIT-licensed build adapter.
// Embeds adapted upstream PowerShell GUI SOURCE as a plain manifest resource.
// This is a compiled .NET Framework Windows executable; PowerShell 5.1 engine
// remains an OS runtime dependency. No external .ps1 or .bat is needed to run.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Management.Automation;
using System.Management.Automation.Runspaces;
using System.Reflection;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Windows.Forms;

internal static class BraveFreeOriginHost
{
    private const string EmbeddedSource = "BFO_SOURCE";

    [STAThread]
    public static int Main(string[] arguments)
    {
        bool selfTest = false;
        string lang = null, testPath = null;
        for (int i = 0; i < arguments.Length; ++i)
        {
            string a = arguments[i];
            if (String.Equals(a, "-Lang", StringComparison.OrdinalIgnoreCase) && i + 1 < arguments.Length)
                lang = arguments[++i];
            else if (String.Equals(a, "-SelfTest", StringComparison.OrdinalIgnoreCase) && i + 1 < arguments.Length)
            {
                selfTest = true;
                testPath = Path.GetFullPath(arguments[++i]);
            }
            else
            {
                MessageBox.Show("Unknown or incomplete command-line option: " + a,
                    "Brave Free Origin", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 2;
            }
        }

        string exe = Assembly.GetExecutingAssembly().Location;
        string root = Path.GetDirectoryName(exe);
        if (String.IsNullOrEmpty(root)) return 2;
        try
        {
            if (!selfTest && !IsAdministrator())
            {
                // UAC is needed for Brave's HKLM enterprise policy controls.
                // Relaunch the SAME exe, never powershell.exe or a wrapper.
                var info = new ProcessStartInfo(exe);
                info.UseShellExecute = true;
                info.Verb = "runas";
                info.WorkingDirectory = root;
                info.Arguments = String.IsNullOrEmpty(lang) ? "" : "-Lang " + Quote(lang);
                Process.Start(info);
                return 0;
            }
            // This directory is application-owned. It is initialized BEFORE the GUI.
            Directory.CreateDirectory(Path.Combine(root, "Data"));
            Directory.CreateDirectory(Path.Combine(root, "Data", "TempShortcuts"));
            // Prevent accidental concurrent state mutations, separated by executable path.
            string lockName = "Local\\BFO.Native." + Sha256(root.ToUpperInvariant()).Substring(0, 32);
            bool created;
            using (var one = new Mutex(true, lockName, out created))
            {
                if (!created)
                {
                    if (!selfTest) MessageBox.Show("Brave Free Origin is already running from this folder.",
                        "Brave Free Origin", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    return 3;
                }
                return RunEmbeddedSource(root, selfTest, testPath, lang);
            }
        }
        catch (System.ComponentModel.Win32Exception e)
        {
            // Includes a denied UAC prompt. Do not bypass UAC or elevate silently.
            if (!selfTest) MessageBox.Show("Permission was not granted or launch failed: " + e.Message,
                "Brave Free Origin", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return 2;
        }
        catch (Exception e)
        {
            string detail = e.ToString();
            try
            {
                Directory.CreateDirectory(Path.Combine(root, "Data", "logs"));
                File.AppendAllText(Path.Combine(root, "Data", "logs", "native-host-error.log"),
                    DateTime.Now.ToString("o") + Environment.NewLine + detail + Environment.NewLine,
                    new UTF8Encoding(false));
            }
            catch { /* never erase or replace existing diagnostic files */ }
            if (!selfTest) MessageBox.Show("Brave Free Origin could not start. Check Data\\logs.\n\n" + e.Message,
                "Brave Free Origin", MessageBoxButtons.OK, MessageBoxIcon.Error);
            else Console.Error.WriteLine(detail);
            return 1;
        }
    }

    private static string Quote(string s) { return "\"" + s.Replace("\"", "\\\"") + "\""; }
    private static bool IsAdministrator()
    {
        using (WindowsIdentity id = WindowsIdentity.GetCurrent())
            return new WindowsPrincipal(id).IsInRole(WindowsBuiltInRole.Administrator);
    }
    private static string Sha256(string text)
    {
        using (var s = SHA256.Create())
        {
            byte[] data = s.ComputeHash(Encoding.UTF8.GetBytes(text));
            return BitConverter.ToString(data).Replace("-", "");
        }
    }
    private static int RunEmbeddedSource(string root, bool selfTest, string testPath, string lang)
    {
        if (selfTest && !File.Exists(testPath)) throw new FileNotFoundException("Missing BFO self test", testPath);
        Assembly assembly = Assembly.GetExecutingAssembly();
        string source;
        using (Stream stream = assembly.GetManifestResourceStream(EmbeddedSource))
        {
            if (stream == null) throw new InvalidOperationException("Embedded BFO source is missing");
            using (var reader = new StreamReader(stream, Encoding.ASCII, true)) source = reader.ReadToEnd();
        }
        var iss = InitialSessionState.CreateDefault();
        using (Runspace runspace = RunspaceFactory.CreateRunspace(iss))
        {
            // WinForms and its GUI event loop must run on THIS STA thread.
            runspace.ApartmentState = ApartmentState.STA;
            runspace.ThreadOptions = PSThreadOptions.UseCurrentThread;
            runspace.Open();
            using (PowerShell ps = PowerShell.Create())
            {
                ps.Runspace = runspace;
                ps.AddScript(source);
                if (!String.IsNullOrEmpty(lang)) ps.AddParameter("Lang", lang);
                if (selfTest) ps.AddParameter("SelfTest", testPath);
                ps.Invoke();
                if (ps.HadErrors)
                {
                    StringBuilder errors = new StringBuilder();
                    foreach (var error in ps.Streams.Error) errors.AppendLine(error.ToString());
                    throw new InvalidOperationException("Upstream GUI reported errors:\n" + errors.ToString());
                }
            }
        }
        return 0;
    }
}
