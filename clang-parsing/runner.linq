<Query Kind="Statements">
  <RuntimeVersion>5.0</RuntimeVersion>
</Query>

var reposRoot = @"C:\Users\Admin\Downloads\_c-repos\";
var pathToExecutable = @"C:\Users\Admin\Desktop\test-clang\test-clang\clang-parsing\x64\Debug\test-clang.exe";
var outputPath = @"E:\cntrloflow_output";


var repos = new DirectoryInfo(reposRoot).GetDirectories();

/*
repos.AsParallel().WithDegreeOfParallelism(10).ForAll(repoPath =>
{
	$"Start processing {repoPath}".Dump();
	var files = System.IO.Directory.GetFiles(repoPath.FullName, "*.c", SearchOption.AllDirectories).ToList();
	files.AddRange(System.IO.Directory.GetFiles(repoPath.FullName, "*.m", SearchOption.AllDirectories));
	var ouputFolder = new DirectoryInfo(Path.Combine(outputPath, repoPath.Name));
	ouputFolder.Create();
			
	var command = $"{string.Join(" ", files)} -- {ouputFolder.FullName}\\";	// command.Dump(ouputFolder.FullName);	// netdata_netdata
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
*/



// 
var finalFolder = new DirectoryInfo(Path.Combine(outputPath, "__result"));
finalFolder.Create();
var filePattern = new Regex(@"^(?<name>.+)__(?<hash>\d+)__(?<date>\d+)(__)?\.ttl$", RegexOptions.Compiled);
foreach (var repo in repos)
{
	var folderPath = Path.Combine(outputPath, repo.Name);
	var ttlFiles = Directory.Exists(folderPath) ? Directory.GetFiles(folderPath, "*.ttl") : new string[0];
	foreach (var file in ttlFiles)
	{
		var shortFileName = file.Split('\\').Last();
		var match = filePattern.Match(shortFileName);
		if (!match.Success)
			continue;
		
		var name = match.Groups["name"];
		var hash = match.Groups["hash"];

		if (finalFolder.GetFiles($"{name}__{hash}__*.ttl").Length == 0 && Directory.GetFiles(folderPath, $"{shortFileName}.log.txt").Length > 0)
		{
			File.Copy(file, Path.Combine(finalFolder.FullName, shortFileName));
			File.Copy(file + ".log.txt", Path.Combine(finalFolder.FullName, shortFileName + ".log.txt"));
			//$"Moved file {shortFileName}".Dump();
		}
		else 
		{
			//$"Collision found for file {shortFileName}".Dump();
		}
	}
	$"Processed repo {repo.FullName}".Dump();
}
