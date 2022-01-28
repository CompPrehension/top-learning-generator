<Query Kind="Statements">
  <RuntimeVersion>5.0</RuntimeVersion>
</Query>

var reposRoot = @"C:\Users\Admin\Downloads\_c-repos\";
var pathToExecutable = @"C:\Users\Admin\Desktop\test-clang\test-clang\clang-parsing\x64\Debug\test-clang.exe";
var outputPath = @"E:\cntrloflow_output";


var repos = new DirectoryInfo(reposRoot).GetDirectories();

repos.AsParallel().WithDegreeOfParallelism(1).ForAll(repoPath =>
{
	$"Start processing {repoPath}".Dump();
	var files = System.IO.Directory.GetFiles(repoPath.FullName, "*.c", SearchOption.AllDirectories).ToList();
	files.AddRange(System.IO.Directory.GetFiles(repoPath.FullName, "*.m", SearchOption.AllDirectories));
	var ouputFolder = new DirectoryInfo(Path.Combine(outputPath, repoPath.Name));
	ouputFolder.Create();
	
	var command = $"{string.Join(" ", files)} -- {ouputFolder.FullName}\\";
	var process = RunCmdProcess(pathToExecutable, command);
	process.WaitForExit();
	$"Finish processing {repoPath}".Dump();
});


Process RunCmdProcess(string pathToExe, string args)
{
	Process p = new Process();
	p.StartInfo.FileName = pathToExe;
	p.StartInfo.Arguments = args;
	p.Start();
	return p;
}



